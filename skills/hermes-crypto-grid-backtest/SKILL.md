---
name: hermes-crypto-grid-backtest
description: Grid backtest crypto OHLCV, rank combos, export Pine.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [backtesting, crypto, grid-search, ema, rsi, atr, pine-script]
    related_skills: [ema200-trendline-signal]
---

# Hermes Crypto Grid Backtest

Exhaustive parameter-grid backtester for crypto OHLCV data. Tests every symbol x timeframe x parameter combination of an EMA-crossover + RSI-momentum + ATR-stop/target strategy, screens the results through safety gates, ranks the winners, and exports the winning config to Pine Script v5 so live/paper trading uses the exact combo that won the backtest.

Crypto only (forex/stocks removed by design). Pure pandas/numpy, no talib/pyarrow, so it runs on Termux/Pydroid3 ARM64. **Hypothetical research only -- it never places, modifies, or transmits real orders.**

All code lives in `scripts/`. The full original documentation is preserved verbatim in `references/README.md` -- read it before changing anything, since it documents every modeling assumption.

## When to Use
- User wants to sweep many strategy parameters across multiple crypto symbols/timeframes and find the best combo.
- User has OHLCV CSV data and wants win rate, profit factor, drawdown, Sharpe, trades/day per combination.
- User wants a winning backtest combo exported to TradingView Pine Script.

Don't use for: single live signal off fresh Delta candles (use `ema200-trendline-signal`), forex/stocks backtesting (deliberately out of scope), or anything needing real order execution.

## Prerequisites

Deps: pandas, numpy, pyyaml, tabulate. **On Termux use `pkg`, not `pip`** -- pip has no wheels for this platform and falls back to a from-source build (cmake -> numpy -> pandas) that can take 20+ minutes:

```bash
# if pkg errors with "No mirror or mirror group selected", write this first:
echo "deb https://packages-cf.termux.dev/apt/termux-main stable main" > $PREFIX/etc/apt/sources.list
pkg update -y
pkg install -y python-numpy python-pandas   # precompiled aarch64: numpy 2.4.4, pandas 3.0.6
pip install --break-system-packages pyyaml tabulate   # pure-Python, builds in seconds
```

Outside Termux (normal Linux/macOS), plain `pip install pandas numpy pyyaml tabulate` is fine. Verify before running the grid:

```bash
python3 -c "import pandas, numpy, yaml, tabulate; print('ready')"
```

Data: one CSV per symbol+timeframe under a data dir, named exactly `SYMBOL_TIMEFRAME.csv` (e.g. `BTCUSDT_1h.csv`). Header row, case-insensitive: `timestamp, open, high, low, close, volume`. Timestamps must parse as ISO8601 or epoch s/ms; UTC is assumed unless an offset is present.

`scripts/example_data/` ships two synthetic random-walk CSVs for format checking only -- **they are not real market data.** Put real data (Delta Exchange India export or API) in your own `data/` dir.

## How to Run

All commands run from the `scripts/` directory so the local modules import:

```bash
cd <skill_dir>/scripts
```

Smoke test first (2 symbols, 1 timeframe, 8 combos -- finishes in seconds, validates the whole pipeline):

```bash
python3 run_grid_backtest.py --config quick_test_config.yaml --data-dir example_data --out outputs
```

Full grid (edit `grid_config.yaml` for your symbols/timeframes/parameters):

```bash
python3 run_grid_backtest.py --config grid_config.yaml --data-dir data --out outputs
```

Export the winning combo to Pine Script v5:

```bash
python3 pine_export.py outputs/selected_strategy_config_BTCUSDT.json > BTCUSDT_hermes.pine
```

Long runs on a phone: `nohup python3 run_grid_backtest.py ... > run.log 2>&1 &` so the backtest survives the app closing.

## Strategy (base variant, `ema_rsi_atr.v1`)

- **Long**: `ema_fast` crosses UP through `ema_slow` (fresh golden cross) AND RSI > `rsi_buy` (bullish momentum confirms the cross).
- **Short**: `ema_fast` crosses DOWN through `ema_slow` (fresh death cross) AND RSI < `rsi_sell`. Shorts gated by `risk.allow_short`.
- **Stop-loss / Take-profit**: `stop_atr` / `target_atr` x ATR(`atr_period`) from the entry fill price.
- One open position at a time. No pyramiding. No re-entry until `cooldown_bars` elapse after the previous trade closes.

Design note preserved from the original: an earlier draft used RSI oversold/overbought extremes as a *counter-trend* filter, but that combination almost never fires because an EMA trend and an opposite-extreme RSI are largely mutually exclusive. The crossover + momentum-confirmation variant was chosen because it produces a usable trade count while still using every requested grid parameter exactly as named. An RSI-extreme variant will return near-zero trades -- that is expected, not a bug.

## Fill and look-ahead model

OHLCV-only (no tick data), so: signal is knowable at the **close of bar t** -> order fills at the **open of bar t+1**. Stops/targets are evaluated using bar t+1's high/low onward. If both stop and target are touched inside the same bar, the conservative default (stop first) is used and the fill is marked `exit_reason="stop_first_ambiguous"`; the count is reported as `ambiguous_fills`.

Sizing: risk-based, not fixed size -- `qty = equity * risk_pct_per_trade / stop_distance`, where `risk_pct_per_trade` defaults to 0.01 (1% of current equity per trade). Costs: `commission_pct` charged per fill (round-trip = 2x) plus `slippage_bps` per fill, both applied in the fill price and equity.

## Grid expansion and constraints

`parameters:` lists are Cartesian-product grid dimensions. `constraints:` are simple string comparisons evaluated against each candidate (`ema_fast < ema_slow`, `rsi_buy < rsi_sell`, `target_atr > stop_atr`). The `target_atr > stop_atr` rule means an SL-larger-than-TP combo is never tested. Combinations that fail a constraint are pruned before running, not counted as failures.

Constraint expressions are passed through `eval()` with an empty globals dict (only the combo's params are available). Only put simple comparisons there -- never arbitrary code.

## Indicator cache (performance)

Each distinct EMA/RSI/ATR period is computed **once per (symbol, timeframe)** and reused across every parameter combo, via `precompute_indicator_cache()`. Without this, the grid recomputes indicators per trial and never finishes on a phone. Keep this call in `run_grid_backtest.py`; do not remove it when editing.

## Screening and ranking gates

1. **Trade-sample gate**: 100+ trades for a reliable ranking. Fewer trades are kept but flagged `low_sample=True` -- never discarded.
2. **Max drawdown gate**: `screening.max_drawdown_pct` (default 0.20 = 20%). A combo exceeding it fails with `gate_status=max_drawdown_exceeded`. This was a hardcoded 60% ("explosive_drawdown") before the plan; it is now 20% and config-driven. Failed combos stay in `all_trials.csv`, just flagged -- they never reach `top10`/`selected_strategy`.
3. **Non-negative gate**: with `screening.require_non_negative: true`, combos with negative net profit after costs fail with `negative_net_after_costs`.
4. **2-3 trades/day preferred band**: `target_band_min`/`target_band_max` (default 2.0-3.0). Combos in-band are ranked first. If a symbol has none in-band, the nearest overall candidates are shown and the report notes it -- the band is never silently widened or forced.

Ranking tuple (higher = better): net return %, profit factor, max drawdown (less negative sorts first), Sharpe, then closeness to 2.5 trades/day.

## Output files (`outputs/`)

- `all_trials.csv` -- every trial, winners and losers (nothing deleted).
- `top10_<SYMBOL>.csv` -- per-symbol Top 10.
- `top10_global.csv` -- global Top 10 across all symbols.
- `selected_strategy_config_<SYMBOL>.json` -- the #1 combo's full reproducible config, including `config_hash`, `execution: {signal_timing: after_candle_close, fill: next_bar_open}`. This is the input to `pine_export.py`.
- `trade_log_<hash>.csv` -- individual trades for that symbol's #1 combo (engine re-run once to dump them).
- `run_manifest.json` -- run id, config, data status, and all assumptions.
- `grid_config_used.json` -- the exact config actually used.
- `failure_log.csv` -- combos that failed a gate, with reason/error.
- `report.md` -- human-readable summary with data coverage, grid inventory, and all Top-10 tables.

`config_hash` is a sha256 prefix (16 chars) over the canonicalized `{market, symbol, timeframe, strategy_version, parameters, cost_model, risk}` dict -- use it to detect config drift between backtest and live.

## Metric simplifications (read before quoting numbers)

- Equity curve is marked at trade-close events only, not per-bar mark-to-market, so `max_drawdown_pct` is sampled at exits.
- Sharpe/Sortino/Calmar are approximated from per-trade returns annualized by trade frequency (`sqrt(trades_per_day * 365)`), not from a daily equity series. Treat them as relative ranking signals, not exact risk-adjusted returns.
- `trades_per_active_day` uses calendar days (crypto is 24/7), so weekends are included.

## Pitfalls

- **Termux has no pandas/numpy wheels.** `pip install` falls back to a from-source build (cmake -> numpy -> pandas, meson + Cython + g++) that takes 20+ min on ARM and looks like a hang. Use `pkg install -y python-numpy python-pandas` instead (precompiled aarch64). If `pkg` says no mirror selected, write the sources.list line from Prerequisites first.
- **`example_data/` is synthetic.** Any result from the smoke test is pipeline validation only, not a real strategy read. Real conclusions require the user's actual data.
- **An RSI-extreme / counter-trend variant produces almost no trades.** Only the crossover+momentum variant in this skill is wired up. If `all_trials.csv` shows 0 trades across the board, suspect the strategy wiring or data range, not the engine.
- **The last CSV candle is dropped by default** (`hermes_data_io` drops the final row) because a CSV alone cannot tell whether the last candle closed. Documented assumption.
- **Data <50 rows raises `DataUnavailable`** and that symbol+timeframe is skipped with a `data_unavailable` status, not a crash.
- **Runtime scales with bars.** The README benchmark is ~0.015 sec/trial on 1h/365d; 15m has ~10x the bars, so ~10x the time. The full default grid is ~43,700 trials (~40-70 min on the benchmark machine, 2-3+ hours on a phone). Start small (one symbol, one timeframe, small grids), inspect, then widen.
- **Nothing is discarded silently.** Winners and losers both land in `all_trials.csv`; gates only set `gate_status`. Don't filter the file expecting a clean top list -- read `top10_*.csv` for ranked survivors.
- **`constraints` use `eval()`.** They are safe only because they are simple comparisons. Never extend them with arbitrary expressions or file/network access.

## Verification

1. Deps import: `python3 -c "import pandas, numpy, yaml, tabulate"` exits clean.
2. Smoke test: `python3 run_grid_backtest.py --config quick_test_config.yaml --data-dir example_data --out outputs` exits 0 and prints a `[grid_inventory]` block and a `Done. N trials ...` line.
3. `outputs/` contains `all_trials.csv`, `run_manifest.json`, `report.md`, and at least one `top10_*.csv` or `top10_global.csv`. Confirm trial counts in `all_trials.csv` match the `[grid_inventory]` numbers from stdout.
4. If a `selected_strategy_config_<SYMBOL>.json` was written, `python3 pine_export.py <that file>` prints a `//@version=5` strategy whose `emaFastLen`/`emaSlowLen`/`rsiBuyLevel`/etc. match the JSON's `parameters` exactly -- no manual re-typing.

## Safety

- Hypothetical research only. Never place, modify, or transmit real orders from this skill.
- Real fills and returns will differ from the backtest; the OHLCV-only fill model and same-bar stop/target ambiguity are known sources of divergence.
- The `target_band` 2-3 trades/day is a preferred ranking band, not a guarantee -- the strategy's natural frequency may not reach it.
- Delta Exchange India access stays read-only per the standing config: no `DELTA_MCP_MODE=trade`, no API keys, no credentials in output.
