"""
hermes_engine.py
=================
Core engine for the Hermes crypto grid-backtester: indicators, the
EMA + RSI + ATR strategy, and the bar-by-bar (no-look-ahead) backtest loop.

This module is imported by run_grid_backtest.py. It is deliberately kept
pure-pandas/numpy so it runs on Pydroid3 / Termux (ARM64) with no exotic
dependencies (no talib, no pyarrow).

STRATEGY DEFINITION (documented assumption, per Hermes "Default Assumptions" -
the parameter names ema_fast/ema_slow/rsi_period/rsi_buy/rsi_sell/atr_period/
stop_atr/target_atr/cooldown_bars come straight from the skill's grid-spec
example, but the skill itself does not pin down the exact entry rule, so this
is the base/plain variant used here -- an EMA-crossover trend entry with an
RSI momentum filter):

  LONG entry:  ema_fast crosses UP through ema_slow (fresh golden cross)
               AND rsi_period-RSI > rsi_buy (bullish momentum confirms the cross)
  SHORT entry: ema_fast crosses DOWN through ema_slow (fresh death cross)
               AND rsi_period-RSI < rsi_sell (bearish momentum confirms the cross)
  (Note: an earlier draft used RSI extremes (oversold/overbought) as a
  counter-trend filter here -- that combination was tested against sample data
  and almost never fires, because an EMA-trend and an opposite-extreme RSI are
  largely mutually exclusive. This crossover+momentum-confirmation version was
  chosen instead because it actually produces a usable trade count, while still
  using every one of the requested grid parameters exactly as named.)
  Stop-loss:   entry_price -/+ stop_atr   * ATR(atr_period)
  Take-profit: entry_price +/- target_atr * ATR(atr_period)
  One open position at a time. No pyramiding, no re-entry until cooldown_bars
  have elapsed after the previous trade closes.
  Fill model (OHLCV-only, no tick data available): signal is knowable at the
  close of bar t -> order fills at the OPEN of bar t+1. Stops/targets are
  evaluated using bar t+1's high/low onward; if both stop and target are
  touched inside the same bar, the conservative default (stop first) is used
  and the fill is marked exit_reason="stop_first_ambiguous".
"""

from __future__ import annotations
import hashlib
import json
import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Indicators — pure, deterministic, same function for batch or bar-by-bar use
# --------------------------------------------------------------------------- #

def ema(close: pd.Series, period: int) -> pd.Series:
    """EMA with alpha = 2/(period+1), seeded with the prior-period SMA."""
    out = pd.Series(np.nan, index=close.index, dtype=float)
    if len(close) < period:
        return out
    alpha = 2.0 / (period + 1.0)
    seed = close.iloc[:period].mean()
    out.iloc[period - 1] = seed
    prev = seed
    for i in range(period, len(close)):
        prev = alpha * close.iloc[i] + (1 - alpha) * prev
        out.iloc[i] = prev
    return out


def rsi(close: pd.Series, period: int) -> pd.Series:
    """Wilder RSI. avg_loss == 0 -> RSI = 100 (per skill default)."""
    out = pd.Series(np.nan, index=close.index, dtype=float)
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    if len(close) <= period:
        return out
    avg_gain = gain.iloc[1:period + 1].mean()
    avg_loss = loss.iloc[1:period + 1].mean()
    out.iloc[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, len(close)):
        avg_gain = (avg_gain * (period - 1) + gain.iloc[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss.iloc[i]) / period
        out.iloc[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out


def atr(df: pd.DataFrame, period: int) -> pd.Series:
    """Wilder-smoothed true range."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    if len(df) <= period:
        return out
    seed = tr.iloc[1:period + 1].mean()
    out.iloc[period] = seed
    prev = seed
    for i in range(period + 1, len(df)):
        prev = (prev * (period - 1) + tr.iloc[i]) / period
        out.iloc[i] = prev
    return out


# --------------------------------------------------------------------------- #
# Config hashing — so a selected config can be reproduced / detected as changed
# --------------------------------------------------------------------------- #

def config_hash(cfg: dict) -> str:
    canonical = json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Indicator cache -- many grid combos reuse the same ema/rsi/atr period, so we
# compute each distinct period ONCE per (symbol, timeframe) instead of once per
# trial. This is the difference between a runnable grid and one that never
# finishes on a phone.
# --------------------------------------------------------------------------- #

def precompute_indicator_cache(df: pd.DataFrame, ema_periods, rsi_periods, atr_periods) -> dict:
    cache = {}
    for p in set(ema_periods):
        cache[("ema", p)] = ema(df["close"], p).to_numpy()
    for p in set(rsi_periods):
        cache[("rsi", p)] = rsi(df["close"], p).to_numpy()
    for p in set(atr_periods):
        cache[("atr", p)] = atr(df, p).to_numpy()
    return cache


# --------------------------------------------------------------------------- #
# Backtest engine
# --------------------------------------------------------------------------- #

def run_backtest(df: pd.DataFrame, params: dict, costs: dict, risk: dict,
                  indicator_cache: dict | None = None) -> dict:
    """
    df: OHLCV dataframe with columns [timestamp, open, high, low, close, volume],
        already validated/sorted (see data_io.load_ohlcv).
    params: {ema_fast, ema_slow, rsi_period, rsi_buy, rsi_sell, atr_period,
             stop_atr, target_atr, cooldown_bars}
    costs:  {commission_pct, slippage_bps}   (round-trip commission applied per fill)
    risk:   {initial_capital, risk_pct_per_trade, allow_short}

    Returns a dict with: trades (list of dicts), equity_points, warmup_bars,
    n_bars, ambiguous_fills.
    """
    if indicator_cache is not None:
        ema_f = indicator_cache[("ema", params["ema_fast"])]
        ema_s = indicator_cache[("ema", params["ema_slow"])]
        rsi_v = indicator_cache[("rsi", params["rsi_period"])]
        atr_v = indicator_cache[("atr", params["atr_period"])]
    else:
        ema_f = ema(df["close"], params["ema_fast"]).to_numpy()
        ema_s = ema(df["close"], params["ema_slow"]).to_numpy()
        rsi_v = rsi(df["close"], params["rsi_period"]).to_numpy()
        atr_v = atr(df, params["atr_period"]).to_numpy()

    ts_arr = df["timestamp"].to_numpy()
    open_arr = df["open"].to_numpy(dtype=float)
    high_arr = df["high"].to_numpy(dtype=float)
    low_arr = df["low"].to_numpy(dtype=float)

    warmup = max(params["ema_slow"], params["rsi_period"], params["atr_period"]) + 1
    n = len(df)

    equity = float(risk["initial_capital"])
    equity_points = [(ts_arr[0], equity)]
    trades = []
    ambiguous_fills = 0

    in_position = False
    side = None
    entry_price = stop_price = target_price = None
    entry_idx = None
    qty = 0.0
    cooldown_until = -1
    pending_entry = None  # side to enter at NEXT bar's open

    commission_pct = costs.get("commission_pct", 0.0004)   # 4 bps per fill, conservative default
    slippage_bps = costs.get("slippage_bps", 2.0) / 10000.0
    allow_short = risk.get("allow_short", True)
    risk_pct = risk.get("risk_pct_per_trade", 0.01)

    for i in range(warmup, n):
        # --- 1. Fill a pending entry at THIS bar's open (decided at bar i-1 close) ---
        if pending_entry is not None and not in_position:
            side = pending_entry
            pending_entry = None
            fill_price = open_arr[i] * (1 + slippage_bps if side == "long" else 1 - slippage_bps)
            a = atr_v[i - 1]
            if np.isnan(a) or a <= 0:
                side = None  # can't size/stop without ATR -> skip this signal
            else:
                stop_dist = params["stop_atr"] * a
                stop_price = fill_price - stop_dist if side == "long" else fill_price + stop_dist
                target_price = (fill_price + params["target_atr"] * a if side == "long"
                                 else fill_price - params["target_atr"] * a)
                risk_amount = equity * risk_pct
                qty = risk_amount / stop_dist if stop_dist > 0 else 0.0
                if qty > 0:
                    entry_price = fill_price
                    entry_idx = i
                    in_position = True
                    equity -= abs(qty * entry_price) * commission_pct  # entry commission

        # --- 2. Manage an open position using THIS bar's high/low ---
        if in_position:
            hit_stop = (low_arr[i] <= stop_price) if side == "long" else (high_arr[i] >= stop_price)
            hit_target = (high_arr[i] >= target_price) if side == "long" else (low_arr[i] <= target_price)
            exit_price = exit_reason = None
            if hit_stop and hit_target:
                exit_price, exit_reason = stop_price, "stop_first_ambiguous"
                ambiguous_fills += 1
            elif hit_stop:
                exit_price, exit_reason = stop_price, "stop_loss"
            elif hit_target:
                exit_price, exit_reason = target_price, "take_profit"

            if exit_price is not None:
                exit_price *= (1 - slippage_bps if side == "long" else 1 + slippage_bps)
                pnl = (exit_price - entry_price) * qty if side == "long" else (entry_price - exit_price) * qty
                pnl -= abs(qty * exit_price) * commission_pct  # exit commission
                equity += pnl
                trades.append({
                    "entry_time": ts_arr[entry_idx], "exit_time": ts_arr[i],
                    "side": side, "entry_price": entry_price, "exit_price": exit_price,
                    "qty": qty, "pnl": pnl, "pnl_pct": pnl / max(equity - pnl, 1e-9),
                    "exit_reason": exit_reason, "bars_held": i - entry_idx,
                })
                equity_points.append((ts_arr[i], equity))
                in_position = False
                cooldown_until = i + params["cooldown_bars"]
                side = entry_price = stop_price = target_price = entry_idx = None
                qty = 0.0

        # --- 3. Look for a NEW signal at THIS bar's close (fills next bar) ---
        if (not in_position) and (pending_entry is None) and (i >= cooldown_until):
            ef, es = ema_f[i], ema_s[i]
            ef_prev, es_prev = ema_f[i - 1], ema_s[i - 1]
            r = rsi_v[i]
            if np.isnan(ef) or np.isnan(es) or np.isnan(ef_prev) or np.isnan(es_prev) or np.isnan(r):
                continue
            cross_up = ef_prev <= es_prev and ef > es
            cross_down = ef_prev >= es_prev and ef < es
            long_ok = cross_up and r > params["rsi_buy"]
            short_ok = allow_short and cross_down and r < params["rsi_sell"]
            if long_ok:
                pending_entry = "long"
            elif short_ok:
                pending_entry = "short"

    return {
        "trades": trades,
        "equity_points": equity_points,
        "warmup_bars": warmup,
        "n_bars": n,
        "ambiguous_fills": ambiguous_fills,
        "final_equity": equity,
    }
