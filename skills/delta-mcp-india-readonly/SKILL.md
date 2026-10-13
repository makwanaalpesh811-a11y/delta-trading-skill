---
name: delta-mcp-india-readonly
description: "delta mcp india readonly"
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux]
---

name: delta-mcp-india-readonly
description: "Delta Exchange MCP setup. Read-only market data only."
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux, macos]
---
Always-on gates: no API key saved; DELTA_MCP_MODE=trade never set; backup config; only public market-data tools.
Preferred install: `uvx delta-exchange-mcp` — uv/uvx is the supported path on Android aarch64 Termux (verified: uvx 0.12.15 aarch64-linux-android). Confirm Python >=3.12 via pyproject.toml. If `uvx` is missing or `uvx --version` fails, diagnose (`which uvx`, `free -h`, `df -h`) and report — do not silently fall back to `pip install` for MCP deps, and never use an unsupported binary or source tarball.
Pitfalls: never expose DELTA_API_KEY value in output; never use unknown installers; MCP connect requires the `uvx` binary actually resolvable at launch. Verify `uvx --version` before assuming MCP is reachable.

**Resolution param format:** `/v2/history/candles` takes a **string literal** for `resolution` — one of `5s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `1d`, `1w`. Passing integer seconds (e.g. `resolution=60` or `resolution=3600`) returns `HTTP 400` with `bad_schema` error and the list of allowed values. Base URL is `https://api.india.delta.exchange/v2` (no `/api/` prefix — `/api/v2/...` returns 404).

**Response shape and ordering:** `/v2/history/candles` returns `{"success": true, "result": [{close, high, low, open, time, volume}, ...]}`. Candle list is directly under `result` (not `result.candles`), and `time` is Unix **seconds** (not microseconds — the ticker endpoint is the one that uses microseconds). **Response is DESCENDING** (most-recent first) — sort ascending before EMA/ATR math. Range limits: Delta API retains ~5.5 months of 1h candles (Mar-Sep 2026 verified); requesting older silently returns shorter ranges, not an error.

**CRITICAL param names (verified 2026-10-02):** The `/v2/history/candles` endpoint requires BOTH `start` AND `end` params — `from`/`to` (documented in older versions) returns `bad_schema` with `"start is required"` / `"end is required"` errors. Correct form: `?symbol=ETHUSD&resolution=1h&start={unix_s}&end={unix_s}`. `resolution` is a **string literal** — one of `5s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `1d`, `1w`.

**Hard 4000-candle cap per request (verified 2026-10-02):** Regardless of the `start`/`end` span, `/v2/history/candles` returns **at most 4000 candles** — requesting a wider range silently returns the most recent 4000 (no error, no truncation marker). 15m candles max out at ~41 days continuous (96 × 42), 1h at ~167 days, 4h at ~666 days. For longer ranges use windowed pagination: step `start` forward in chunks of ~3500 candles (`chunk = 3500 * tf_sec`) to stay under the cap, accumulate rows across calls, then `drop_duplicates` + sort. 0.12–0.2s sleep between calls avoids rate limits; ~15s per full 365d of 1h candles (3 calls).

**Products discovery without auth:** `GET https://api.india.delta.exchange/v2/products?status=1` returns ~1200 products (200 OK, no key). Filter for perpetuals: `symbol.endswith('USD')` AND not `startswith('P-') or startswith('C-')` (those are options). No `product_type` field is populated — filter by symbol shape. `state: "live"` marks active products.

**Historical CSV CDN is unreliable:** `cdn-ind.deltaex.org/historical-data-api/fut/...` often returns `404` or HTTP `000` (connection error) for non-ETH symbols (BTCUSD, SOLUSD, etc. tested). Use the `/v2/history/candles` API endpoint instead — works for all perpetuals without auth, one request per month is enough (no pagination needed for 1h × 31 days). Multi-coin 1h fetch for 8 months × 10 coins ≈ 80 requests ≈ 30 seconds with 0.15s spacing.

Procedure for public-only read when module unavailable: direct `curl https://api.india.delta.exchange/v2/tickers/<SYMBOL>`; confirm symbol first; never send DELTA_API_KEY; save raw JSON; treat `timestamp` as microseconds (not ms) — dividing by 1000 causes out-of-range datetime; report current/high/low/time in Hindi/English with tool name (`get_ticker`); zero trade/order/account mutation.
Live MCP verification without Hermes restart — class-level technique: when `mcp_servers` is already in `~/.hermes/config.yaml` but tools aren't registered in the current Hermes session, invoke the server directly via `subprocess.Popen(['uvx', '--from', 'delta-exchange-mcp', 'delta-exchange-mcp'], env={..., 'DELTA_MCP_ENV': 'india_prod', 'DELTA_MCP_MODE': 'read'})` and drive it with a JSON-RPC script on stdin: initialize → notifications/initialized → tools/call, writing each line with a small delay (0.2-0.5s) so the async server flushes responses. Read stdout on a daemon thread and parse each line starting with `{`. This returns live tickers, candles, orderbook — proves end-to-end connectivity without a Hermes restart. Never send auth keys over stdin; the env-var approach keeps credentials out of the process args (visible in `ps`). For concurrent multi-symbol pulls, either spawn one subprocess per symbol or serialize tool_calls with distinct `id` and enough `time.sleep()` between them (>=5s after the last call before terminate); too-aggressive stdin close loses the async server's response flush.

`get_candles` return shape (verified): `result.content[0].text` parses to `{"result": [<candle>, ...], "meta": {...}}` — the candle list is directly under `result`, NOT under `result.candles`. Each candle is `{close, high, low, open, time, volume}` with `time` in Unix seconds. Sort ascending by `time` before EMA/ATR math (the response is not guaranteed ordered).

TradingView MCP (`tradingview-mcp-jackson` and derivatives) is incompatible with Android Termux: it requires TradingView Desktop app + Chrome DevTools Protocol. Report this as a blocker and pivot to (a) Delta MCP public OHLCV for the same analysis, (b) TradingView app screenshots + vision analysis, or (c) Pine Script written here and executed manually on the user's desktop. Never claim Pine Script execution is available on this device.

References/youtube-hindi.md addition note: for Hindi YouTube transcripts via youtube-transcript-api, use `api.fetch(video_id, languages=['hi','en'])` then iterate snippets directly (no `.to_raw_data()` — the `TranscriptList` object has no such method). Save with `for sn in transcripts: f.write(f"[{sn.start:.1f}] {sn.text}")`. `api.list(id)` returns available language codes and `is_generated` flag but not text.

References/diagnosis-aarch64.md depth note (reusable): On Android aarch64 Termux with Python 3.14 when `pip install` times out at ~180-420s for MCP deps (e.g., delta-exchange-mcp 0.6.0), diagnose in order without retry: check `free -h` + swap (low RAM is primary blocker), `ps` for stuck pip process, `df -h`, `curl` to pypi.org, and inspect dependency metadata (`pydantic-core` / `cryptography` = native build triggers). Never fall back to source tarball or unsupported binary; stop and report cause. Config md5 check (`md5sum`) confirms no mutation.

References/binance-public-mcp.md depth note (reusable): For public-only market data without Delta Exchange / uv / rust / native Python builds, inspect `node` + `npx` availability, then `node2flow/binance-mcp` (or `binance-intelligence-mcp`). These expose 11 public-data tools (`bn_klines`, ticker, order book) with NO API key; trading/account tools require `BINANCE_API_KEY`. Always confirm `npm` presence; `node` + `npx` without `npm` may block package resolution. Never place orders; never set `BINANCE_API_KEY` for read-only inspection; `~/.hermes/config.yaml` untouched.

References/delta-backtest-pitfalls.md depth note (reusable): When using Delta's `/v2/history/candles` to feed any backtest/grid, apply the rules in that file before running: (1) ATR via pandas `.max(axis=1)` skips NaN, numpy `np.maximum.reduce()` propagates it — a shift(1) leading NaN kills ATR silently; (2) compute indicators once on the FULL df, THEN split 70/30, not the reverse; (3) wrap `fetch_delta` in try/except to survive transient `[Errno 104] Connection reset by peer` on long grids; (4) funnel-debug one combo before widening to a grid; (5) user's strategy-review protocol — diff first, preserve entry conditions verbatim, --quick before full grid; (6) rank by `min(train_pf, test_pf)`, not `test_pf` alone, and report cross-coin consensus separately from single-coin winners.
