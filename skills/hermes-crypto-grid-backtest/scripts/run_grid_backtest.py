#!/usr/bin/env python3
"""
run_grid_backtest.py
=====================
Hermes crypto-only grid backtest runner.

Usage:
    python run_grid_backtest.py --config grid_config.yaml --data-dir ./data --out ./outputs

For every symbol x timeframe x parameter combination in the grid it:
  1. loads + validates OHLCV data (last 365 days, or max available -- default)
  2. runs the EMA+RSI+ATR engine (hermes_engine.run_backtest) with no look-ahead
  3. computes metrics + screening gates + trade-sample gate (100+ trades, else
     marked low_sample) (hermes_metrics.py)
  4. keeps EVERY trial (winners and losers) in all_trials.csv
  5. ranks and writes top10_<symbol>.csv per symbol + a global top10_global.csv
  6. writes run_manifest.json, grid_config used, selected_strategy_config.json
     for each symbol's #1, trade_log_<hash>.csv for each symbol's #1,
     failure_log.csv, and a human-readable report.md

This only ever produces hypothetical research results. It never places,
modifies or transmits real orders.
"""

from __future__ import annotations
import argparse
import itertools
import json
import os
import sys
import time
import traceback

import pandas as pd
import yaml

from hermes_engine import run_backtest, config_hash, precompute_indicator_cache
from hermes_metrics import compute_metrics, passes_safety_gates, rank_score
from hermes_data_io import load_ohlcv, slice_last_n_days, DataUnavailable


def expand_grid(param_grid: dict, constraints: list[str]) -> list[dict]:
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    combos = []
    for combo in itertools.product(*values):
        d = dict(zip(keys, combo))
        ok = True
        for c in constraints:
            try:
                if not eval(c, {}, d):  # constraints are simple comparisons, e.g. "ema_fast < ema_slow"
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            combos.append(d)
    return combos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="grid_config.yaml")
    ap.add_argument("--data-dir", default="./data")
    ap.add_argument("--out", default="./outputs")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    os.makedirs(args.out, exist_ok=True)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    param_grid = cfg["parameters"]
    constraints = cfg.get("constraints", [])
    symbols = cfg["symbols"]
    timeframes = cfg["timeframes"]
    lookback_days = cfg.get("lookback_days", 365)
    costs = cfg.get("cost_model", {"commission_pct": 0.0004, "slippage_bps": 2.0})
    risk = cfg.get("risk", {"initial_capital": 100000.0, "risk_pct_per_trade": 0.01, "allow_short": True})
    screening = cfg.get("screening", {"require_non_negative": True,
                                       "target_band_min": 2.0, "target_band_max": 3.0,
                                       "max_drawdown_pct": 0.20})

    param_combos = expand_grid(param_grid, constraints)
    requested_cartesian = 1
    for v in param_grid.values():
        requested_cartesian *= len(v)

    print(f"[grid_inventory] requested cartesian per (symbol,timeframe): {requested_cartesian}")
    print(f"[grid_inventory] valid after constraints: {len(param_combos)}")
    print(f"[grid_inventory] symbols x timeframes: {len(symbols)} x {len(timeframes)} = "
          f"{len(symbols) * len(timeframes)}")
    total_trials = len(param_combos) * len(symbols) * len(timeframes)
    print(f"[grid_inventory] total trials this run: {total_trials}")

    all_trials = []
    failures = []
    data_status = {}

    for symbol in symbols:
        for timeframe in timeframes:
            key = f"{symbol}_{timeframe}"
            try:
                df = load_ohlcv(args.data_dir, symbol, timeframe)
                df = slice_last_n_days(df, lookback_days)
                data_status[key] = {"status": "ok", "rows": len(df),
                                     "start": str(df["timestamp"].iloc[0]),
                                     "end": str(df["timestamp"].iloc[-1])}
            except DataUnavailable as e:
                data_status[key] = {"status": "data_unavailable", "reason": str(e)}
                print(f"[data_unavailable] {key}: {e}")
                continue

            start_ts, end_ts = df["timestamp"].iloc[0], df["timestamp"].iloc[-1]

            # Compute each distinct ema/rsi/atr period ONCE for this symbol+timeframe,
            # then reuse across every param combo below (see hermes_engine docstring).
            ind_cache = precompute_indicator_cache(
                df, param_grid["ema_fast"] + param_grid["ema_slow"],
                param_grid["rsi_period"], param_grid["atr_period"])

            for params in param_combos:
                cfg_for_hash = {
                    "market": "crypto", "symbol": symbol, "timeframe": timeframe,
                    "strategy_version": "ema_rsi_atr.v1", "parameters": params,
                    "cost_model": costs, "risk": risk,
                }
                chash = config_hash(cfg_for_hash)
                try:
                    result = run_backtest(df, params, costs, risk, indicator_cache=ind_cache)
                    metrics = compute_metrics(result, risk["initial_capital"], start_ts, end_ts)
                    ok, gate_reason = passes_safety_gates(
                        metrics,
                        require_non_negative=screening.get("require_non_negative", True),
                        max_drawdown_pct=screening.get("max_drawdown_pct", 0.20))
                    row = {
                        "config_hash": chash, "symbol": symbol, "timeframe": timeframe,
                        **params, **metrics, "gate_status": "pass" if ok else gate_reason,
                    }
                    all_trials.append(row)
                    if not ok:
                        failures.append(row)
                except Exception as e:
                    failures.append({
                        "config_hash": chash, "symbol": symbol, "timeframe": timeframe,
                        **params, "gate_status": "error", "error": str(e),
                    })

    trials_df = pd.DataFrame(all_trials)
    trials_path = os.path.join(args.out, "all_trials.csv")
    trials_df.to_csv(trials_path, index=False)

    failures_df = pd.DataFrame(failures)
    failures_df.to_csv(os.path.join(args.out, "failure_log.csv"), index=False)

    # --- Ranking: Top 10 per symbol, then global Top 10 ---
    top10_per_symbol = {}
    if not trials_df.empty:
        passed = trials_df[trials_df["gate_status"] == "pass"].copy()
        band_min = screening.get("target_band_min", 2.0)
        band_max = screening.get("target_band_max", 3.0)
        in_band = passed[(passed["trades_per_active_day"] >= band_min) &
                          (passed["trades_per_active_day"] <= band_max)]

        for symbol in symbols:
            pool = in_band[in_band["symbol"] == symbol]
            note = "within 2-3 trades/day band"
            if pool.empty:
                pool = passed[passed["symbol"] == symbol]
                note = "no candidate in 2-3 trades/day band -- showing nearest overall"
            if pool.empty:
                top10_per_symbol[symbol] = (pd.DataFrame(), note)
                continue
            pool = pool.copy()
            pool["_score"] = pool.apply(lambda r: rank_score(r.to_dict()), axis=1)
            pool = pool.sort_values("_score", ascending=False).drop(columns="_score")
            top10 = pool.head(10)
            top10.to_csv(os.path.join(args.out, f"top10_{symbol}.csv"), index=False)
            top10_per_symbol[symbol] = (top10, note)

        global_pool = in_band if not in_band.empty else passed
        if not global_pool.empty:
            global_pool = global_pool.copy()
            global_pool["_score"] = global_pool.apply(lambda r: rank_score(r.to_dict()), axis=1)
            global_top10 = global_pool.sort_values("_score", ascending=False).drop(columns="_score").head(10)
            global_top10.to_csv(os.path.join(args.out, "top10_global.csv"), index=False)
        else:
            global_top10 = pd.DataFrame()
    else:
        global_top10 = pd.DataFrame()

    # --- selected_strategy_config.json + trade_log for each symbol's #1 ---
    for symbol, (top10, _note) in top10_per_symbol.items():
        if top10.empty:
            continue
        best = top10.iloc[0]
        timeframe = best["timeframe"]
        params = {k: (int(best[k]) if float(best[k]).is_integer() else float(best[k]))
                  for k in param_grid.keys()}
        selected = {
            "strategy_version": "ema_rsi_atr.v1", "market": "crypto",
            "symbol": symbol, "timeframe": timeframe, "timezone": "UTC",
            "parameters": params,
            "execution": {"signal_timing": "after_candle_close", "fill": "next_bar_open"},
            "cost_model": costs, "risk": risk,
            "config_hash": best["config_hash"],
        }
        with open(os.path.join(args.out, f"selected_strategy_config_{symbol}.json"), "w") as f:
            json.dump(selected, f, indent=2)

        # Re-run once more to dump the full trade log for this specific finalist.
        df = load_ohlcv(args.data_dir, symbol, timeframe)
        df = slice_last_n_days(df, lookback_days)
        result = run_backtest(df, params, costs, risk)
        pd.DataFrame(result["trades"]).to_csv(
            os.path.join(args.out, f"trade_log_{best['config_hash']}.csv"), index=False)

    # --- run_manifest.json ---
    manifest = {
        "run_id": run_id, "market": "crypto", "symbols": symbols, "timeframes": timeframes,
        "lookback_days": lookback_days, "cost_model": costs, "risk": risk,
        "screening": screening, "requested_cartesian_per_market": requested_cartesian,
        "valid_combos_after_constraints": len(param_combos),
        "total_trials_run": len(all_trials), "data_status": data_status,
        "assumptions": [
            "Data source: user-provided OHLCV CSVs under --data-dir",
            f"Date range: last {lookback_days} calendar days, or max available if shorter",
            "Trade sample gate: 100+ trades for normal reliability; fewer trades kept and flagged low_sample",
            "Timezone: UTC (crypto, 24/7)",
            "Initial capital: see risk.initial_capital, 1% risk-per-trade sizing by default",
            "Signal fill: next bar open (OHLCV-only, no tick data)",
            "Both stop and target touched in one bar -> stop-first (conservative), flagged ambiguous",
            "2-3 trades/day is a preferred ranking band, not a forced count",
        ],
    }
    with open(os.path.join(args.out, "run_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    with open(os.path.join(args.out, "grid_config_used.json"), "w") as f:
        json.dump(cfg, f, indent=2)

    # --- human-readable report ---
    lines = [f"# Hermes Crypto Grid Backtest Report ({run_id})", ""]
    lines.append("## Data coverage")
    for k, v in data_status.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append(f"## Grid: requested {requested_cartesian} combos/market, "
                 f"{len(param_combos)} valid after constraints, {len(all_trials)} total trials run")
    lines.append("")
    lines.append("## Global Top 10")
    lines.append(global_top10.to_markdown(index=False) if not global_top10.empty else "_no candidate passed the gates_")
    for symbol, (top10, note) in top10_per_symbol.items():
        lines.append(f"\n## Top 10 -- {symbol} ({note})")
        lines.append(top10.to_markdown(index=False) if not top10.empty else "_no candidate passed the gates_")
    lines.append(f"\n## Failed trials: {len(failures)} (see failure_log.csv)")
    lines.append("\n_All results are hypothetical research only; real fills and returns may differ._")
    with open(os.path.join(args.out, "report.md"), "w") as f:
        f.write("\n".join(lines))

    print(f"\nDone. {len(all_trials)} trials, {len(failures)} failed gates. Outputs in {args.out}/")


if __name__ == "__main__":
    main()
