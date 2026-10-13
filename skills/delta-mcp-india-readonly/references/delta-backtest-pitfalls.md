# Delta backtest pitfalls

Rules distilled from real multi-coin / multi-TF grid sessions. Each is a silent-zero-trade or mis-ranked-top-1 risk that only shows up at grid scale.

## 1. Indicator NaN propagation (pandas vs numpy)

**Bug:** ATR computed with `np.maximum.reduce([h-l, |h-pc|, |l-pc|])` returns `[nan, nan, nan, ...]` for ALL bars when `pc = df["close"].shift(1).values` starts with a NaN at index 0.

**Why it's silent:** `np.maximum.reduce()` propagates NaN (like `np.maximum`); pandas `.max(axis=1)` on a DataFrame skips NaN by default. So the pandas concat form works and the numpy-equivalent form does not — same numbers, different shape.

**Symptom:** Strategy runs to completion in a fraction of a second, `0 trades`, all PF=0, all R=0. Funnel debug shows thousands of signals firing but zero `pos` being set.

**Root cause chain:** `atr[t] = NaN` → `risk = NaN * atr_mult = NaN` → `if risk > 0:` is False → entry block never runs → no position ever opens → 0 trades. The strategy wiring itself is 100% correct; only ATR is broken.

**Fix:** Always use the pandas concat form when the TR formula involves `shift(1)`:

```python
def add_indicators(df, ema_n, atr_n=14):
    df = df.copy()
    df["ema"] = df["close"].ewm(span=ema_n, adjust=False).mean().values
    pc = df["close"].shift(1)   # pandas Series — shift produces NaN at row 0
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)  # skips NaN
    df["atr"] = tr.ewm(alpha=1.0 / atr_n, adjust=False).mean().values  # ewm handles NaN
    return df
```

**Rule:** When porting indicator math between numpy and pandas, treat `shift()` → concat → `.max(axis=1)` as one unit. Don't rewrite it in pure numpy unless you explicitly handle the leading NaN (e.g., fill it with `close.iloc[0]` or `high-l.iloc[0]`). A 30-second debug that checks `np.isnan(df['atr'].values).sum()` catches this before the grid runs.

## 2. Indicators on FULL df, THEN split — not per-split

**Bug:** Computing EMA/ATR separately on `df_train` and `df_test` gives two independent indicator streams, not a train tail and a test continuation of one series.

**Why it matters:** EWM/EMA are recursive. Warmup on train is 305 bars for EMA300; running them separately on each split wastes that warmup twice and — worse — makes the train/test indicator values differ from what a live forward-pass would produce. Test-only indicators are missing train-period price history entirely.

**Correct order:**

```python
# WRONG: split first, indicators twice
df_train = df.iloc[:split].reset_index(drop=True)
df_test  = df.iloc[split:].reset_index(drop=True)
df_train_i = add_indicators(df_train, ema)   # EMA starts fresh at row 0 of train
df_test_i  = add_indicators(df_test, ema)    # EMA starts fresh at row 0 of test

# RIGHT: indicators once on full, then split
df_i = add_indicators(df, ema)                # EMA sees all history
train_i = df_i.iloc[:split].reset_index(drop=True)
test_i  = df_i.iloc[split:].reset_index(drop=True)
```

**Rule:** Compute indicators once on the full sample, then slice. This also means `add_indicators()` is cached per (symbol, tf, ema), not recomputed per combo — 3x speedup for a grid over ema=[100, 200, 300].

## 3. Delta `Connection reset by peer` is transient

**Bug:** Long grid runs hit `[Errno 104] Connection reset by peer` from `api.india.delta.exchange` on ~1 of every 40-60 requests. Retrying that exact request usually works.

**Fix:** Wrap every `fetch_delta()` call in a try/except that prints `SKIP <coin> <tf>: <error>` and continues to the next (coin, tf). Don't `sys.exit()`, don't raise to the outer loop — one coin's outage shouldn't kill the whole grid. Log the skip so the report makes it obvious which cells are missing.

**Rule:** Grid runners must be resilient to per-cell failure. `fetch_delta` = try/except per call; the runner keeps going. At end of run, count skips and surface them in the summary. A single skipped cell out of 45 coin×tf combinations is acceptable; a crashed runner is not.

## 4. Funnel debug before grid

**Bug:** 5,280 combos running at 0.05s each = ~4.5 min of compute to discover the strategy produces 0 trades on all cells.

**Rule:** Before running a grid on a new strategy, run ONE combo with counters at each decision gate:

```
c > EMA?              N_ctx bars
2+ swing highs?       N_ctx (or fewer if pivots sparse)
p2 < p1?              N
age filter passed?    N
c > trendline?        N
c > p2?               N
now=True (fresh)?     N
FRESH cross?          N
SIG generated?        N
Positions opened?     N
Trades closed?        N
```

If the funnel collapses at step 5 or later but the strategy spec is unchanged, suspect indicator values (see pitfall 1) or pivot definition. If it collapses at step 1 (`c > EMA`), suspect EMA being NaN or the wrong direction. This 10-second debug replaces an hour of grid-scale debugging.

## 5. User's strategy-review protocol

For any user-supplied strategy that Hermes must modify or reuse:

1. **Diff first, run second.** Compare line-by-line against the user's original before executing. List every change in a table ("kept identical" / "changed" with reason). User explicitly rejects silent rewrites.
2. **Preserve entry conditions verbatim.** Even if a condition seems redundant or logically weak (e.g., `c > p2` when `c > trendline` already implies it), don't drop or simplify. The user may have specific intent.
3. **Funnel debug before grid.** Run default params + 1 coin first. Only widen if signals flow.
4. **Report PnL in dollars AND R multiples.** User asks for "Total PnL kitna hai" after seeing PF/R — give $ value from `initial_capital × final_equity_factor` and the equity curve's peak-to-trough drawdown in both $ and %.
5. **`--quick` mode is mandatory before full grid.** A `--quick` flag that runs 1 coin + 1 TF + all combos validates the pipeline in ~30 seconds. Full grid without it wastes 30+ min on a silent-zero bug.

## 6. Ranking rule for grid results

Sort by `min(train_pf, test_pf)` for the primary ranking, not by `test_pf` alone. A combo with `train_pf=1.9, test_pf=1.05` has more evidence than one with `train_pf=1.02, test_pf=1.9`, and the min-of-two is more honest about robustness.

Filter for cross-coin consensus: same (tf, ema, atr_mult, rr, pl/pr) that shows PF>1 on ≥2 coins is a stronger signal than any single-coin winner. Report these separately — single-coin winners are the noise floor; cross-coin winners are the signal.
