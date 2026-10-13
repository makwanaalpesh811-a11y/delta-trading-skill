# V1 Backtest Procedure — EMA300 + Pivot(3,3) + ATR14×2 SL + RR 2.0

Use this when the user asks for a multi-coin backtest of the v1 strategy ("list do, backtest karo" / "15m pe v1 test karo").

## Canonical params (DO NOT substitute other values)

```python
P = dict(emaLen=300, atrLen=14, atrMult=2.0, rr=2.0,
         pvL=3, pvR=3, minBars=8, maxAge=400, maxSpan=800, tolATR=0.1)
FEE_PCT = 0.1    # percent
SLIP_PCT = 0.05  # percent
RISK_PCT = 1.0   # percent of current equity, per trade
CAPITAL_PER_COIN = 10000.0
```

Source of truth: `~/paper_trade/terminal_dashboard_v1.py` `P = dict(...)` block. Other older scripts on disk (`multi_coin_test.py` etc.) use `maxAge=100, maxSpan=200` — those were an earlier experiment, NOT the v1 default. Do not copy params from there.

## Data source

Delta Exchange India API, `GET /v2/history/candles?symbol=SYM&resolution=15m|1h&start=<unix>&end=<unix>`. Paginate backwards from `now`, 4000 TF-seconds per page. Response is DESCENDING — sort ascending after every page. Drop the last (still-forming) bar: `if c['time'] + tf_sec > now: skip`. Available range: ~5-6 months per TF. 1h yields ~8000 bars/coin covering ~10 months; 15m yields ~8000 bars covering only ~83 days. Fetch is ~50-100 pages per symbol at these resolutions; with `ThreadPoolExecutor(max_workers=10)` + `time.sleep(0.04)` between pages, ~342 coins × 2 TFs finishes in 5-10 minutes.

## THE CRITICAL PITFALL — inline walk-forward, not "final-state-on-history"

Do NOT call `analyze_bar(cands, P)` once and use the returned final `dn`/`up` for all historical bars. The final `dn`/`up` reflects the LAST bar's trendline state; applied retroactively to bar 500 or bar 2000, it produces garbage. Symptoms:

- BTCUSD on 1h, 8mo data: 36 trades instead of ~280.
- ETHUSD and XRPUSD: 0 trades instead of ~275-298.
- SOLUSD: 1 trade instead of ~275.

Correct pattern — pivot detection, expiry, entry, and exit all happen INSIDE a single `for i in range(n)` loop, with `dn`, `up`, `phX/phY`, `plX/plY` as evolving state. Order inside the loop:

1. Exit check (only if `pos is not None and i > pos["bar"]`)
2. Pivot detection for THIS bar — detect pivot at `i - pvR`, then search `phX` for a valid earlier reference, update `dn` (and `up` symmetrically). Only mutate `dn` here.
3. Entry check (only if `pos is None and i > emaLen`): `if c > E[i] and dn is not None and c > mtl.line_val(dn, i)` → LONG. Symmetric for short.
4. Expiry: `if dn is not None and i - dn[2] > maxAge: dn = None`. Same for `up`.

## Reference script

`~/paper_trade/backtest/run_bt.py` is the validated script. Usage: `python3 run_bt.py <coins_file> [out_file]`. It handles both TFs in one pass, parallel fetches with 10 workers, paginates to ~30000 bars, writes raw JSON results + prints per-TF summary + canary check. If a future session needs to modify it, keep the inline walk-forward loop intact — that is the correctness invariant.

## Canary check (run every time)

After each backtest run, compare BTC/ETH/XRP/SOL/LINK trade counts and win rates against the known-good baseline (8mo 1h):

| Coin     | Trades | Win % | Notes                              |
|----------|--------|-------|------------------------------------|
| BTCUSD   | ~280   | 36.7% |                                    |
| ETHUSD   | ~275   | 33.8% |                                    |
| XRPUSD   | ~298   | 35.6% |                                    |
| SOLUSD   | ~276   | 35.1% |                                    |
| LINKUSD  | ~292   | 36.0% |                                    |

Any deviation in trade COUNT by more than ±20% or win rate by more than ±5% = bug in the loop. Fix before reporting results.

## R-values compound — don't chase a specific R baseline

The reference implementation uses `risk_dollar = equity * RISK_PCT / 100` computed from CURRENT equity each trade, so R values scale exponentially with consecutive wins. The older `fetch_and_backtest_new.py` uses the same compounding model, which is why the historical +13.75R/+13.39R/+13.68R/+10.34R/+8.59R numbers are only comparable to a fresh run with fixed-size risk (or to the exact same code path). If a canary run shows +27R on BTC where +13.75R was expected, the count and win rate are still valid; the R value just grew because equity compounded. Report trade count + win rate + PnL as the primary signals; R is secondary.

## Data shape mix — dicts from API, tuples in local list

The Delta API returns a list of dicts. The local `all_c` list is typically kept as tuples `(time, o, h, l, c, v)` for speed. Two crash patterns:

1. `c[0]` on a dict → `KeyError: 0`. Always use `c['time']` when iterating `page` (the raw API response) and `t[0]` when iterating `all_c` (the tuple list).
2. Mixing them in one comprehension — e.g. `min(c[0] for c in page_asc)` where `page_asc` is dicts → `KeyError: 0`. Either convert `page_asc` to tuples FIRST (`[(c['time'], ...) for c in page_asc]`) or use `c['time']` consistently.

## Output layout

Per TF, print: (a) coins fetched / with trades / empty / errors; (b) total trades, W/L, %W; (c) total PnL and total R; (d) best/worst single trade; (e) top 15 profitable coins and bottom 10 losers with per-coin n/W/L/%W/PnL/R. Sort by PnL descending for top, ascending for bottom. Save raw JSON at `~/paper_trade/backtest/results.json` keyed by `{tf: {sym: {trades, err}}}`.

## Multi-TF note

If the user asks for 15m AND 1h on the same coin list, run both TFs in the same script pass (not two scripts) so the parallel fetcher shares the connection pool. 15m has far less history than 1h at the same bar-count cap — always report the date range covered per TF so the user can normalize comparisons. `TF_SECONDS = {'1m': 60, '3m': 180, '5m': 300, '15m': 900, '1h': 3600}`.

## Long-running background execution

For 200+ coins × 2 TFs, expect 5-15 minutes. Use `terminal(command="python3 run_bt.py ...", timeout=1800)` — Hermes will promote to background if over the 600s foreground cap. The process prints progress every 25 coins (`done/total (elapsed)`); when done, the notify arrives with exit code + output tail. Do NOT re-launch on timeout — poll with `process(action='poll')` if you need to check status sooner.
