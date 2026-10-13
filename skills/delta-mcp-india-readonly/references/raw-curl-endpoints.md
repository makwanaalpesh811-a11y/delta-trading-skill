# Raw curl endpoints for Delta India (india_prod)

When `uvx` / MCP subprocess is unavailable, use these URLs directly. All work unauthenticated.

## Base URL
- **`https://api.india.delta.exchange/v2/`** — this is the base, NOT `/api/v2/`. Adding `/api/` prefix returns 404 `Not Found` (9 bytes).
- Testnet: `https://cdn-ind.testnet.deltaex.org/v2/`
- Devnet: `https://cdn-ind.devnet.deltaex.org/v2/`

## Key endpoints (all `?status=1` optional)

### Products list (paginated)
`GET /v2/products?status=1&contract_types=perpetual_futures&page_size=3000`

Return: `{"meta": {"after": null, "limit": 3000, "total_count": N}, "success": true, "result": [<product>, ...]}`

**Pitfall:** each product's `product_type` field is `null` in the returned JSON — the `contract_types` filter is applied server-side but the field isn't populated. To filter perpetuals client-side, use symbol name:

```python
perps = [p for p in products
         if p['symbol'].endswith('USD')
         and not p['symbol'].startswith('P-')   # exclude calls
         and not p['symbol'].startswith('C-')]  # exclude puts
```

Note `contract_types=perpetual_futures` (snake_case) is the correct filter value — `linear-futures` or `linear_futures` won't match (though they may not 404, they return everything).

### OHLCV candles (paginated, this is the one to use for backtesting)
`GET /v2/history/candles?symbol=BTCUSD&resolution=1h&start=<unix_sec>&end=<unix_sec>`

Return: `{"success": true, "result": [{"close": ..., "high": ..., "low": ..., "open": ..., "time": <unix_sec>, "volume": ...}, ...]}`

**Pitfall: `resolution` must be a STRING enum, not integer seconds.** Valid values:
```
"5s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "1d", "1w"
```
Sending `resolution=3600` or `resolution=60` returns 400 with `Allowed values are 5s,1m,3m,5m,15m,30m,1h,2h,4h,6h,1d,1w`.

Candles come back **descending by time** (newest first) — sort ascending before EMA/ATR math.

**Pagination:** the endpoint caps each response; loop by moving `start` to `last_candle.time + resolution_seconds`. For 8 months of 1h = ~5,800 candles = ~2 pages for BTCUSD. Rate-limit by sleeping 0.15s every 5 pages.

**Range caveat:** `start`/`end` must be Unix seconds, not ms. `start <= end` inclusive on both sides. Very wide ranges (>~1 year at 1m) may silently return partial data — chunk by month to be safe.

### Recent trades (last N, no pagination)
`GET /v2/market/trade/recent-trades?ticker_symbol=BTCUSD&limit=100`

### Orderbook
`GET /v2/market/orderbook?product_id=3136` (product_id, not symbol)

### Ticker
`GET /v2/tickers/<SYMBOL>` — single symbol

## Common product IDs (india_prod, verified 2026-09)
- ETHUSD → 3136
- BTCUSD → 27
- SOLUSD → 14823
- XRPUSD → 14969
- BNBUSD → 15042

Look these up dynamically via `/v2/products` if symbols drift.

## What DOES NOT work (returns 404 or empty)
- `/api/v2/...` (wrong prefix — drop the `/api/`)
- `/v2/market/products` (use `/v2/products`)
- `/v2/market/historical-candles/` (use `/v2/history/candles`)
- `/v2/market/trade/tickers?ticker_symbol=X` (use `/v2/tickers/X` or `/v2/market/trade/tickers/X`)
- `cdn-ind.deltaex.org/historical-data-api/futures/trades/monthly/{SYM}-{YYYY-MM}_<suffix>.csv.gz` — the monthly CSV suffix is a per-file opaque token (`1790090587656`) the user already has on disk for ETHUSD, but you cannot guess new ones. Use `/v2/history/candles` instead.
- `cdn-ind.deltaex.org/historical-data-api/fut/{SYM}/{YYYY-MM}.csv.gz` — path variant that also 404s

## Working example: fetch 8 months of BTCUSD 1h

```bash
curl -sS --max-time 30 -A "Mozilla/5.0" \
  "https://api.india.delta.exchange/v2/history/candles?symbol=BTCUSD&resolution=1h&start=1735689600&end=1740787200" \
  -o btc_1h.json
```

## Headers
Always send `-A "Mozilla/5.0"` — missing User-Agent gets 403 on some endpoints.
No auth header required for public market data.
