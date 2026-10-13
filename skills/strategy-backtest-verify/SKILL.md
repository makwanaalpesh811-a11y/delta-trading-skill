---
name: strategy-backtest-verify
description: Use before grid/param sweep on a user-provided strategy.
version: 1.0.0
---

# Strategy Backtest Verify Workflow

When the user gives a strategy script and asks for a grid backtest, follow this EXACT order. Never skip steps. User will reject if you modify strategy logic — reproduce exactly.

## Rule 0: Never modify strategy logic

If the user provides a strategy (e.g. `backtest()` function), copy it VERBATIM into the grid runner. Do not rewrite ATR, EMA, indicators, or entry/exit conditions "for speed" — user will reject.

## Step 1: Diff rewrite vs original

Before running anything, list every difference between your rewrite and the user's original. Focus on:
- Indicator math (EMA, ATR, pivots)
- Entry/exit conditions
- Position management
- Lookahead / shift()
- Any variable renames

Present as a checklist. If user sees a change they didn't authorize, STOP and revert.

## Step 2: Default-params single run

Run the grid on ONE coin + ONE TF + default params. Print:
- Trades count
- Win/Loss split
- PF, total R, avg R

If trades = 0, DO NOT proceed to full grid. Debug instead.

## Step 3: Funnel debug counters

If default params give 0 (or suspiciously low) trades, add per-condition counters in the backtest loop:

For LONG (mirror for SHORT):
```
c > EMA bars
  2+ swing highs
    p2 < p1 (downtrend)
      age filter passed
        c > trendline
          c > p2 (above swing)
            now=True
              now AND NOT prev (fresh cross)
                SIG generated
                  Positions opened
                    Trades closed
```

Print each stage with count + % of previous stage. This shows exactly where signals die.

## Step 4: Only then run full grid

After confirming trade flow with funnel:
- Cache data per (coin, tf) at ~/bt_cache/
- Append results to CSV incrementally (crash-safe)
- Report: top combos, stability analysis, lucky-point warning

### Indicator + split rule (CRITICAL)

Compute `add_indicators()` on the FULL df FIRST, THEN do the 70/30 train/test split.

```python
# WRONG — indicators computed independently on each split:
df_train_i = add_indicators(df_train, ema)   # EMA warmup restarts at 0
df_test_i  = add_indicators(df_test, ema)     # test set EMA ≠ train EMA

# RIGHT — full df first, then slice:
df_i = add_indicators(df, ema)                # EMA built over entire history
df_train = df_i.iloc[:split].reset_index(drop=True)
df_test  = df_i.iloc[split:].reset_index(drop=True)
```

**Why:** EMA at bar 0 of `df_test` is meaningless if computed in isolation — you want EMA to reflect the full price history up to that bar, including train-period bars. Splitting first also wastes compute (recompute per split).

**Same rule applies to ATR** — the ATR column at position 0 of `df_test` must be the same as its value in the full-df ATR, not a fresh EWM from scratch.

### Report structure (user preferences)

1. **Top 15 filter**: `trades >= MIN_TRADES` AND `train_pf > 1` AND `test_pf > 1` AND `train_trades >= MIN_TRAIN_TRADES` AND `test_trades >= MIN_TEST_TRADES`. Require MIN_TRAIN_TRADES and MIN_TEST_TRADES (default 15 each) — a combo with 30 total trades but 28 in train and 2 in test is not testable.

2. **Best per (coin, tf)**: sort by `min(train_pf, test_pf)`, NOT by train_pf or test_pf alone. A combo with train=10, test=0.1 is worse than train=1.5, test=1.5 — the min captures both robustness and out-of-sample strength.

3. **Lucky-point detection**: For each top combo, enumerate 1-step neighbors in parameter space (same coin/tf/pl/pr, ±1 step on ema, atr_mult, rr — 2^3 = 8 neighbors). Count how many have PF < 1. If >50% of neighbors have PF < 1, mark the combo as 🚨 LUCKY. If <=50%, mark as ✅ STABLE. Recommend only STABLE combos.

4. **Cross-coin consensus**: Group valid combos by (tf, ema, atr_mult, rr, pl, pr) and count distinct coins. Combos with `coins >= 2` where both train_pf > 1 and test_pf > 1 are much stronger candidates — the parameter survives across assets. Report this separately.

5. **Stale CSV handling**: Delete `~/grid_results.csv`, `~/grid_top15.csv`, `~/grid_best_per_symbol.csv`, `~/grid_cross_coin_consensus.csv` at run start. Never append to a stale CSV — you'll get duplicates and stale rows pollute rankings.

### Fetch resilience

Wrap `fetch_delta()` in try/except:
```python
try:
    df, _ = fetch_delta(coin, tf, days, cache_dir=cache_dir)
    if len(df) < MIN_CANDLES:
        print(f"  SKIP {coin} {tf}: too few candles ({len(df)})")
        continue
except Exception as e:
    print(f"  SKIP {coin} {tf}: {e}")
    continue
```

Never let a single coin/tf failure abort the whole grid.

## Common bugs to watch for

1. **`np.maximum.reduce` propagates NaN** — user's pandas `.max(axis=1)` skips NaN. If rewriting ATR in numpy, `pc = close.shift(1)` starts NaN → `np.maximum.reduce` gives all-NaN TR → all-NaN ATR → `risk > 0` always False → 0 trades silently. FIX: use pandas concat+max(axis=1) or use `np.nanmax`.

2. **Delta API param names**: `/v2/history/candles` needs `start`+`end` (unix seconds), NOT `from`/`to`. Wrong names return `bad_schema` with `"start is required"`.

3. **Delta 4000 candle cap per request**: 365d 1h = 8760 candles → needs pagination (2000 candles × ceil(8760/2000) requests).

4. **`~/bt_cache/*.csv` has two timestamp formats mixed** — some older cache files were written with unix seconds (`1776686400,...`), newer ones with ISO datetime strings (`2025-10-03 15:00:00,...`). Naive `np.genfromtxt(..., names=True)` followed by `D["time"].astype(np.int64)` raises `ValueError: invalid literal for int() with base 10: np.str_('2025-...')` on the ISO file. FIX: detect first row and branch —
   ```python
   first = str(D["time"][0]).strip()
   if first.isdigit():
       t = D["time"].astype(np.int64)
   else:
       from datetime import datetime
       t = np.array([int(datetime.fromisoformat(str(x)).timestamp()) for x in D["time"]])
   ```
   Wrap in try/except with cache delete + refetch as fallback. Do not silently skip — the user has both formats in production.

5. **Compounding PnL requires ratio math, not addition** — when a strategy trades multiple times and PnL must compound, use `eq *= (1 + ret)` where `ret = (exit-entry)/entry` for longs and `ret = (entry-exit)/entry` for shorts. Do NOT use `eq += (exit-entry)` — that gives BTC-scale PnL (e.g. `-286%` on BTCUSD 4h from a single losing trade) instead of true return percentage. For percentage-based return reporting, initialize `eq = 1.0` and report `(eq-1)*100`, or track `eq_ratio` separately from cash.

6. **Classic Supertrend has two flavors and only one produces flips.** The "naive" version (`if close < lower_basic: direction=-1`) never flips because `lower_basic` isn't a ratcheting band — close sits above it in a downtrend so direction stays `1` forever, giving ~1 trade/year instead of 40-100. Correct classic Supertrend maintains *final* upper/lower bands with ratcheting:
   ```python
   if basic_upper[i] < final_upper[i-1] or c[i-1] > final_upper[i-1]:
       final_upper[i] = basic_upper[i]
   else:
       final_upper[i] = final_upper[i-1]   # ratchet down on bearish side
   # mirror for final_lower
   # flip only when close pierces the ratched band:
   if prev_dir == 1 and c[i] < final_lower[i]: dir = -1
   if prev_dir == -1 and c[i] > final_upper[i]: dir = 1
   ```
   Initialize `dir=1` at the first valid ATR index (not at index 0, which is NaN-warmup). If your Supertrend gives <10 trades over 365d of hourly data on BTC, the band ratchet is missing — not the parameters.

7. **ADX with `wma(wma(x,n),n)` returns all-zero when x has leading NaN.** In `wma(wma(h-l,n),n)` the inner WMA's first `n` values are NaN; the outer WMA then treats those as NaN and outputs NaN, then often converts to 0 downstream. Symptom: `adx[-5:]` prints `[0. 0. 0. 0. 0.]` — every entry filter using `adx > threshold` fires forever or never. If you can't get working ADX in a short time, drop it from the entry gate rather than ship broken. Simple EMA filter + trend flip is often enough.

## Example bug from 2026-10-02

User gave `ema300_tl_swing_backtest.py`. I rewrote ATR with numpy for speed:
```python
# WRONG — propagates NaN
pc = df["close"].shift(1).values  # pc[0]=NaN
tr = np.maximum.reduce([...])     # all NaN
```
Funnel debug showed 142 signals generated but 0 positions opened (because `risk = atr[t] * atr_mult = NaN * 2 = NaN`, and `NaN > 0` is False).

Fix: use pandas concat+max(axis=1) which skips NaN, and ewm(alpha=1/n).mean() which propagates NaN-safe.

## User interaction

- User language: Hinglish/Gujarati
- Wants short bullets + tables
- Wants the diff printed BEFORE running (not after)
- User will reject any strategy modification — reproduce exactly
- If user says "Option X" referring to a numbered list, follow it literally
