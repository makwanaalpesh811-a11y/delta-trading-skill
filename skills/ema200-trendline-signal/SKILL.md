---
name: ema200-trendline-signal
description: "EMA200 + TrendLine Break Signal (15m, Delta MCP)"
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux]
---

name: ema200-trendline-signal
description: Fetch fresh Delta MCP candles and run the 15m signal script.
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux, macos]
---

# EMA200 + TrendLine Break Signal (15m, Delta MCP)

Pine v5 port at `~/ema_tl_signal.py`. Strategy: EMA200 filter, pivot-based downtrend/uptrend lines, break on close, ATR(7) SL x2, TP x6 (RR 1:3).

## Setup
- Script: `~/ema_tl_signal.py` (stdlib only, no pandas/numpy)
- Data files: `~/candles_btc.json`, `~/candles_eth.json` (Delta MCP 15m candles)
- Fetch helpers: `~/fetch_fresh.py` (BTC+ETH), `~/fetch_eth.py` (ETH retry)
- Delta MCP: `DELTA_MCP_MODE=read`, `DELTA_MCP_ENV=india_prod`, `uvx --from delta-exchange-mcp delta-exchange-mcp`
- 30-day lookback returns ~2880 candles. Bigger lookbacks time out.

## Rules
1. **Signal ke liye HAMESHA pehle Delta MCP se fresh 15m candles fetch karo** BTCUSD + ETHUSD, dono JSON files overwrite. Use `python3 ~/fetch_fresh.py 30` (aur `~/fetch_eth.py 30` if ETH fails). Do not reuse old JSON for a fresh signal.
2. **Phir `python3 ~/ema_tl_signal.py` chalao.** Script ka raw output use karo. Signal khud guess mat karo.
3. **Output se batao:** LATEST SIGNAL (or NONE), active DOWN/UP lines ki `now` aur `next-bar` value, price vs EMA200 (ABOVE/BELOW), ATR value, Data age, aur last signals list ka result (win/loss, net R).
4. **Agar `Data age ... STALE` aaye to candles dobara fetch karo.** STALE threshold is `dur + 2 min` for 15m. Repeat fetch until OK. STALE data pe signal mat batao.
5. **Pivot list ya "abhi ki state" me se signal mat batao.** Signal sirf script ki bar-by-bar simulation from the script itself. `dn`/`up` line existence alone is not a signal — the script has to find the actual break bar.
6. **Script ka koi number ya output apni taraf se badalna mana hai.** No editing script values, no manual recompute, no rounding. Report the raw string as-is.
7. **Script me koi bug lage to pehle user ko bina poochhe code mat badlo.** Report the bug with location and proposed patch, wait for approval.

## Workflow
```
# 1. Fetch fresh (BTC first, ETH fallback if needed)
python3 ~/fetch_fresh.py 30
python3 ~/fetch_eth.py 30   # only if ETHUSD showed FAIL above

# 2. Syntax check (only after code edits)
python3 -m py_compile ~/ema_tl_signal.py

# 3. Run signal script
python3 ~/ema_tl_signal.py --last 15
```

## Output Interpretation
- `Last closed bar: start X | closed Y IST | close ... | EMA200 ... (ABOVE/BELOW) | ATR ...`
- `Data age: N min OK | forming candle dropped` (OK = fresh; `STALE` = re-fetch)
- `DOWN line: A B -> C D | now ... | next-bar ... | age N bars` (or `none`)
- `>>> LATEST SIGNAL: LONG/SHORT @ price | SL ... | TP ...` (or `NONE`)
- `Position OPEN: ...` (currently held trade)
- `Signals (last N of M):` (win/loss log)
- `Closed: N | Win X% | Net ±pts | ±RR` (aggregate)

## Best combo (from ~/sweep.py on 864 sims, 2026-09-23)

**Default pick — ETH 15m, low drawdown:**
```
emaLen=100  atrLen=7  atrMult=1.5  rr=3.0  pvL=5 pvR=5
minBars=8  maxAge=200  maxSpan=400  tolATR=0.1
```
Backtest: 64 trades, 41% win, +40R net, **-1R max drawdown**.

Run: `python3 ~/ema_tl_signal.py ~/candles_eth.json --emaLen 100 --atrMult 1.5 --rr 3.0 --maxAge 200 --maxSpan 400`

**Aggressive pick — ETH 1m, high R:**
```
emaLen=200  atrLen=14  atrMult=1.0  rr=4.0  pvL=5 pvR=5
maxAge=200  maxSpan=400
```
Backtest: 108 trades, 29% win, +46.8R, -7R max DD. Only 3 days of 1m data (less reliable).

Run: `python3 ~/ema_tl_signal.py ~/candles_eth_1m.json --emaLen 200 --atrLen 14 --atrMult 1.0 --rr 4.0 --maxAge 200 --maxSpan 400`

**Avoid:** BTC 1m across all combos (net -30 to -45R, DD up to -58R). BTC 15m baseline net -13R. BTC 5m with ema200 atr14x1.0 rr4.0 pv3,3 is best BTC variant (+42R).

**Full sweep data:** `~/sweep_results.json` (all 864 sims). Re-run with `python3 ~/sweep.py` after refreshing candles.

## Sweep rules
- Sweep grid: atrMult x [1.0, 1.5, 2.0, 3.0], rr x [2.0, 3.0, 4.0], emaLen x [50, 100, 200], pivot x [(3,3), (5,5)], atrLen x [7, 14]. 144 combos.
- Coins/timeframes: BTC+ETH on 1m/5m/15m. 864 sims total, ~28s on Termux.
- Min 15 trades to qualify for ranking.
- Rank by: net_R (profitability), win_pct (hit rate), avg_R (efficiency). Bottom 5 shows worst to avoid.
- Baseline (P defaults) always printed for comparison.

## Best combo with trailing SL (from ~/trail_test.py, 41.7d data)

**ETH 15m + trailing:**
```
emaLen=200 atrLen=7 atrMult=2.0 rr=3.0 pvL=5 pvR=5 maxAge=400 maxSpan=800
trailing: ATR x1.5, activate immediately (act=0), keep TP at 3R
```
119 trades, 87% win, **+269.7R**, 0 max DD.

**BTC 15m + trailing:**
```
emaLen=200 atrLen=7 atrMult=2.0 rr=3.0 pvL=5 pvR=5 maxAge=400 maxSpan=800
trailing: ATR x2.0, activate immediately, keep TP at 3R
```
118 trades, 90% win, **+288.9R**, 0 max DD.

Baseline (fixed SL, no trailing): ETH +1R, BTC -11R. Trailing gives 270x improvement.

## Trailing SL rules
- **Type:** ATR-based (SL = max(SL, high - k*ATR)) or points (SL = max(SL, high - pct*entry)). ATR outperforms points on this strategy.
- **k value:** 1.5-2.0 x ATR optimal. Tighter (1.0) still good; wider (3.0) reduces win rate.
- **Activation:** 0 (immediate) slightly better than 1R or 2R activation. Trail from entry bar.
- **TP:** Keep TP at 3R. Pure trailing (no TP) produced few trades.
- **Only update SL in profit direction:** `if new_sl > old_sl: sl = new_sl` (long), mirror for short. Never move SL against profit.
- **Trailing code:** Update pos["sl"] after each bar (after pivot update). Uses current bar's ATR for trail distance.

## Multi-TF (15m entry, 1m exit)
- Signals on 15m, execute exits on 1m sub-bars (intra-15m precision)
- Trail uses 1m highs/lows, ATR from 15m
- Only 8-9 trades in current 3-day 1m window — not statistically reliable, but avg R is huge (+9 to +11 R per trade)
- Requires 1m data covering the 15m signal period

## Files
- `~/trail_test.py` — full EXP1/2/3 sweeper (stdlib only)
- `~/trail_results.json` — all raw results
- `~/trail_output.txt` — last run output

## Safety
- Delta MCP read-only: `DELTA_MCP_MODE=read`. Never `trade`. Never set API keys.
- Backup `~/ema_tl_signal.py` before any edit.
- No credentials in output.
