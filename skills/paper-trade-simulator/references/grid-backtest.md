# Grid Backtest + Leverage Analysis

Use when the user asks to sweep strategy params on a coin list to find the best SL/RR/risk combination ("grid backtest karo", "best leverage kya rahegi", "SL TP grid").

## Grid shape

Two grids, run separately:

1. **Param grid** — vary `sl_mult` × `rr` at a fixed risk level (default 1%) to find the best structural combo.
   - `sl_mults = [1.0, 1.5, 2.0, 2.5, 3.0]` — ATR multiplier for stop loss
   - `rrs = [1.0, 1.5, 2.0, 2.5, 3.0]` — reward:risk ratio

2. **Leverage sweep** — fix best param combo, vary `risk_pct = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]` to show the risk/return/DD trade-off. R stays the same across risk levels (R is risk-normalized); PnL and $DD scale.

Total runs for both grids: `len(sl_mults) × len(rrs) × len(risks) × n_coins`. For 5×5×4×25 = 2500 runs, ~250 seconds with the cached-candles approach below.

## Cache first, then run

**Never re-fetch candles across runs.** Fetch all coins once, pickle to `~/paper_trade/backtest/candles_cache.pkl`, then run the entire grid against the cache. A 2500-run grid over cached data completes in ~4 minutes; over live API it would take 250+ minutes.

```python
CACHE = os.path.join(HOME, "paper_trade", "backtest", "candles_cache.pkl")
if os.path.exists(CACHE):
    with open(CACHE, "rb") as f:
        cands_map = pickle.load(f)
else:
    # fetch + pickle once
    with open(CACHE, "wb") as f:
        pickle.dump(cands_map, f)
```

## Portfolio-level aggregation — CRITICAL

**DO NOT** sum per-coin max drawdowns or per-coin R values and call that "portfolio R/DD." Summing per-coin DDs is meaningless (different peaks at different bars, different equity curves). Instead:

1. For each combo, keep every coin's full equity curve (list of equity points over bar index).
2. Sum curves across coins at each bar index → portfolio equity curve.
3. Walk the portfolio curve, track running peak, compute `max_dd = peak - equity` and `max_dd_pct = max_dd / peak`.
4. `final_eq = portfolio_curve[-1]`, `pnl = final_eq - n_coins × CAPITAL`.

Curves have different lengths (coins fetch different numbers of bars). Align by taking `maxlen = max(len(p) for p in curves)` and defaulting to the last value of shorter curves for later bars.

```python
maxlen = max(len(p) for p in curves)
port = [sum(p[i] if i < len(p) else p[-1] for p in curves) for i in range(maxlen)]
peak = port[0]; max_dd = 0; max_dd_pct = 0
for e in port:
    if e > peak: peak = e
    dd = peak - e
    if dd > max_dd: max_dd = dd
    if peak > 0 and dd/peak > max_dd_pct: max_dd_pct = dd/peak
```

## Leverage formula

Report leverage per combo as `max_lev = entry * qty / equity` at the entry bar. This is notional/capital, which is what the user cares about. With the standard sizing (`risk_dollar = equity * RISK_PCT / 100`, `qty = risk_dollar / |entry - sl|`), leverage scales as `risk_pct / (sl_pct_of_price)`. Example: `sl_mult=2.0` with `atr_pct_of_price ≈ 2%` means `sl_pct_of_price ≈ 4%`, so `leverage ≈ 1% / 4% = 25%`... but in practice ATR% is more like 1-3%, so leverage is typically 10-50x. **The 1% risk number is deceptive — 1% risk on a tight SL can mean 25-50x leverage on notional.**

## Ranking metrics

Always report BOTH:

1. **By total R** — highest raw edge. Best for aggressive users.
2. **By R / MaxDD%** — risk-adjusted. Best for balanced users. The R/DD ratio normalizes out the DD, and this is what separates "works in backtest" from "would blow up in live".

Example output (real values from top-25 coins, 1h):

```
By total R:
  SL=1.0 RR=3.0 R=3.0%  +1475R  DD=56.0%  Lev=46x   (aggressive, brutal DD)
  SL=1.5 RR=3.0 R=1.0%  +1415R  DD=8.1%   Lev=10x  (best balance)
  SL=2.0 RR=2.0 R=1.0%  +1116R  DD=5.5%   Lev=7.7x  (v1 default)

By R / MaxDD%:
  SL=2.0 RR=3.0 R=0.5%  +1143R  DD=2.6%  R/DD=448  (best risk-adjusted)
  SL=3.0 RR=2.0 R=0.5%  +700R   DD=1.7%  R/DD=416
```

## Findings from the top-25 1h grid (26 Sep 2026)

- **RR=3.0 dominates** — highest RR wins even at low win rate (29-30% W). Tight RR=1.0 produces the worst results (negative R on SL=1.0).
- **SL×1.0-1.5 produces most R** — tight SL produces 2-3× more trades, and RR=3.0 pays off the extra losses.
- **Risk% does NOT change R** — R is risk-normalized, so 0.5% R and 3% R produce identical R totals. Risk only scales $ PnL and $ DD.
- **1% risk on ATR×2 SL = 7-15x leverage** — not 1x. The risk_pct is not the leverage number.
- **SL=1.0 RR=3.0 R=3% = 46x leverage, 56% DD** — catastrophic in real money.
- **25/25 coins profitable** at SL=1.0 RR=3.0 R=1% — broad edge.
- **Best risk-adjusted: SL=2.0 RR=3.0 R=0.5%** — +1143R, 2.6% DD, R/DD=448.

## Survivorship bias caveat

When the coin list is picked AFTER seeing backtest results (in-sample top-25), the results are overstated. Always disclose: "coin list was filtered post-backtest, so R/DD numbers are upper bounds, not expected out-of-sample performance." The user should backtest the SAME coin list on data the filter did NOT see (out-of-sample) before deploying.

## Files

- `~/paper_trade/backtest/grid_bt.py` — the param-grid runner
- `~/paper_trade/backtest/grid_analyze.py` — portfolio-level DD + leverage aggregation
- `~/paper_trade/backtest/candles_cache.pkl` — cached candles for top-25 (or any coin list the user provided)
- `~/paper_trade/backtest/grid_results.json`, `grid_summary.csv`, `grid_portfolio.json` — outputs
- Copy the CSV + JSON summary to `/sdcard/Hermes_Files/uploads/` for user visibility.
