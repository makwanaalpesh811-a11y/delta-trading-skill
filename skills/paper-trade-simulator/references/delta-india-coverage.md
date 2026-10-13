# Delta India API — Coverage & Limits

Use when the user asks to backtest or trade on a subset of Delta futures contracts ("below $0.10 coins", "25 coins neeche", "delta pe kaunse coins"), or when the number of available contracts seems unexpectedly small or large.

## Endpoints (both exist, both work from India)

| Endpoint | What it returns | Candle endpoint |
|---|---|---|
| `api.delta.exchange` | Small subset (options + a few spot perps) | Not used |
| `api.india.delta.exchange` | Full India futures book | `/v2/history/candles` |

Both are public, no API key. `api.delta.exchange/v2/tickers?product_type=FUTURES` returns ~15 contracts; `api.india.delta.exchange/v2/tickers?product_type=FUTURES` returns 200+. **Use `api.india.delta.exchange`** for coin discovery and backtest data — that's the endpoint `terminal_dashboard_v2.py` and the v1/v2 simulators use. The shorter `api.delta.exchange` is a restricted view and produces wildly misleading "only 15 coins available" conclusions.

Candles endpoint (both endpoints, but `api.india.delta.exchange` is what the code uses):
```
GET https://api.india.delta.exchange/v2/history/candles?symbol=<SYM>&resolution=1h&start=<unix>&end=<unix>
```
`resolution` is a string literal (`5s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `1d`, `1w`). Integer seconds returns HTTP 400. Response is DESCENDING — sort ascending before math. Response key is `result` (not `result.candles`). Fields per candle: `open, high, low, close, time, volume` (Unix seconds).

## Current India futures coverage (Sep 2026)

`api.india.delta.exchange/v2/tickers?product_type=FUTURES` returns **~224 perps + options**:

- **Spot perps: ~224** (excluding `P-`/`C-` option prefixes)
- **Top-liquidity majors (>$1000 turnover/day):** BTC, ETH, SOL, XRP, ZEC, LTC, DOGE, UNI, AAVE, LINK, AVAX, FIL, BCH, DASH, DOT, SUI, BNB, NEAR
- **Below $1 USD: ~99 contracts** (majority of the long-tail book)
- **Below $0.10 USD: ~30+ contracts** — RARE, AKE, MUBARAK, DOGE, BEAT, SAGA, HU, IN, PUMP, GRIFFAIN, TNSR, SEI, BLESS, GALA, XAN, LAB, TLM, SKYAI, AIO, AIN, BILL, BASED, CHIP, VELVET, SOLV, TAC, USUAL, XAI, 1000PEPE, SONIC
- **Below ₹0.10 INR (≈$0.0012): 0 contracts** — all Delta futures are USD-quoted

Filter pattern:
```python
perps = [i for i in d['result']
         if 'C-' not in i['symbol'] and 'P-' not in i['symbol']
         and i.get('close')]
below_0_10 = [i for i in perps if float(i['close']) < 0.10]
```

## Contract_value varies per symbol (critical for 1-lot sizing)

Delta perps do NOT have uniform lot size. Each instrument has a `contract_value` field that scales how much notional 1 lot represents:

| Symbol class | Typical `contract_value` | 1 lot notional at close | Example |
|---|---|---|---|
| Major perps (BTC/ETH/SOL) | 1 | price × 1 | BTC @ $84k → 1 lot = $84k |
| Memecoins (RARE/HU/DOGE/IN/SEI) | 100 | price × 100 | RARE @ $0.02 → 1 lot = $2 |
| Small memecoins (PUMP/GALA/PEPE) | 1000 | price × 1000 | PUMP @ $0.004 → 1 lot = $4 |
| Micro memecoins (AKE/TLM/BLESS) | 10000 | price × 10000 | AKE @ $0.03 → 1 lot = $336 |
| Ultra-micro (TAC/USUAL) | 100000 | price × 100000 | TAC @ $0.0016 → 1 lot = $160 |

**Implications for backtests on a $2 sub-account:**
- $16 max notional (8x × $2) does not fit 1 lot of AKE ($336), TAC ($160), GALA/PEPE/PUMP class unless their contract_value is 100.
- "1 lot = $10 notional" is WRONG for uniform modeling. Backtests must derive `position_notional = contract_value × close[0]` per symbol.
- Some long-tail memecoins are literally untradeable at $2 balance even with 8x — their 1 lot exceeds the max notional the margin can support.

Fetch pattern:
```python
tickers = get('https://api.india.delta.exchange/v2/tickers?product_type=FUTURES')['result']
for i in tickers:
    cv = float(i.get('contract_value', 1))
    close = float(i['close'])
    lot_notional = cv * close
```

## Endpoints that don't work from India

- `api.deltaex.com` — DNS fails.
- `global-api.delta.exchange` — DNS fails.
- Global Delta endpoints consistently return `HTTP:000`. Any "global" data comes from Binance USDT or from `api.india.delta.exchange`.

## Response shape gotchas

- Price field is `close` (not `last_price`). `ltp` (last trade price) is a separate field.
- `turnover_usd` is 24h turnover in USD. For liquidity floor use `turnover_usd > 50000` for realistic sizing; < $10k/day means slippage will dominate.
- `contract_value` on the ticker = 1 lot notional multiplier (see table above).
- `/v2/instruments?product_type=FUTURES` returns 404 on India endpoint — use tickers for product metadata.
- Response is not sorted — sort by `close` or `turnover_usd` explicitly.

## Rate limits

- `api.india.delta.exchange`: ~20000 weight per 5 min per user IP.
- Per call cost ≈ 1 weight for `history/candles`, similar for `tickers`.
- 25 symbols × 2 resolutions × 1 call = ~50 calls, ~50 weight — trivial.
- Full 200-symbol scan at 5 resolutions = ~1000 calls = still under 10% of budget.

## Provenance disclosure — mandatory

When reporting a coin list, ALWAYS disclose which source produced it:

- **"Delta India current"** (`api.india.delta.exchange`): full 224-perp book, live. What a real order would hit today.
- **"Delta India restricted"** (`api.delta.exchange`): 15-contract subset (mostly options + a few majors). Do NOT use for coverage analysis.
- **"Binance USDT historical"**: 200+ coins scanned over months, may include long-tail delisted pairs. Used for the v2 deploy list.
- **"V2 deploy list"** (25 fixed coins in `terminal_dashboard_v2.py`): MEUSD, SUNUSD, WLDUSD, MOVEUSD, NEARUSD, ZECUSD, SONICUSD, METAXUSD, ENAUSD, BLURUSD, REDUSD, VVVUSD, TRUMPUSD, EVAAUSD, BIOUSD, BERAUSD, RIVERUSD, JTOUSD, INJUSD, TIAUSD, STXUSD, HUSD, TRXUSD, BEATUSD, UNIUSD — a mix of Delta-available and Binance-only.

The user can conflate these universes. Always state which one before running a sweep.

## Currency ambiguity rule

When the user writes a price threshold with `$` (e.g. "$0.10 ke neeche", "0.1$ ke niche"), CONFIRM USD vs INR before running any filter. `$` in Hinglish is often USD, but user has used it for INR too ($0.10 USD ≈ ₹8 vs ₹0.10 INR ≈ $0.0012). The resulting universe differs by 100×. If the filter returns 0 or 1 match on `api.india.delta.exchange`, the threshold is almost certainly too strict — the user probably meant a different currency or a looser cutoff.

## Practical implications for paper trading

- **Sub-$0.10 USD universe on Delta India IS tradeable** — 30+ symbols with $10k–$50M turnover. Backtest on 25 of them is realistic.
- **Contract_value varies** — always fetch it per symbol and multiply into `position_notional`. Never assume uniform lot size.
- **At $2 × 8x = $16 max notional**, only symbols with `contract_value × close ≤ 16` fit 1 lot. Filter the coin list by this before running a grid.
- If the user wants a coin list below a threshold, filter by `float(close) < threshold` on `api.india.delta.exchange` tickers, then cross-check with `contract_value × close ≤ max_notional` for margin fit.
