---
name: delta-live-order-execution
description: "Delta Live Order Execution"
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux]
---

name: delta-live-order-execution
description: "Place Delta v2 orders. HMAC-signed, dry-run default."
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux, macos]
---

# Delta Live Order Execution

Placing real orders on Delta Exchange via the v2 REST API. Covers auth signing, order payload building, and the demo-then-mainnet safety ladder. Distinct from the read-only MCP skill (no orders) and the paper-trade-simulator skill (never sends orders) — this is the class that mutates an account.

## Always-on rules

- **Dry-run is the default. `trade_enabled: true` + real keys are BOTH required to send.** `--live` refuses to run if either is missing. A placeholder key like `PASTE_API_KEY_HERE` must count as "no key". Key detection checks the string value is NOT in a placeholder set AND has length > 10 — a bare `if api_key:` passes on a placeholder and is a live-fire bug.
- **Demo (testnet) first, always. Never point at mainnet until demo is proven.** The host string is the only thing that decides demo vs real money. Default config is the testnet host; switching to mainnet is a deliberate, separately-confirmed step after the strategy shows profit on demo. If unsure which host is configured, check the config — do not assume.
- **Never commit or print API secrets.** `config.json` holds keys and is `chmod 600`. Secrets stay out of logs, git, error output, and tool args. Echoing a key value in a print/log line is a credential-exposure bug even in demo.
- **Every entry order carries an attached SL and TP** (`stop_loss` / `take_profit` fields on the same order). Never place a naked position. `reduce_only` for exits, never average down into a losing position.
- **One position per symbol at a time**; respect a max-open-positions cap. Risk per trade is a fixed % of capital (default 1%), sized against `|entry − SL|`, not against notional.
- **Signatures are valid 5 seconds.** Generate the timestamp and signature at request-send time, never reuse a cached signature. Reuse fails with `SignatureExpired`.
- **Log every order action** (dry-run or live) with an IST timestamp to a single append-only file, so the user can audit what was sent or what would have been sent.
- **Stop before anything irreversible.** This skill is for DEMO by default. Mainnet order placement is a separate, explicitly-requested escalation — never self-promote from demo to mainnet.

## Hosts

| Environment | Host | Money |
|---|---|---|
| Demo / Testnet India (default) | `https://cdn-ind.testnet.deltaex.org` | play money |
| Mainnet India | `https://cdn.india.deltaex.org` | REAL money — switch only after demo proven |

Both are public-reachable for market data with no key. The demo app (`demo.delta.exchange`) is the testnet account — its API keys are scoped to testnet play-money and are NOT transferable to mainnet.

## Product coverage differs by environment (verified)

- **Testnet demo** lists ~16 live perpetuals only: BTCUSD, ETHUSD, SOLUSD, XRPUSD, ADAUSD, DOGEUSD + some stock/gold/index products. Most alts are ABSENT — LINK, AVAX, DOT, SUI, BNB, LTC, UNI do not exist on testnet.
- **Mainnet** lists ~220 live perpetuals (the full set).

**Pitfall:** a coin that trades fine on mainnet returns nothing on testnet. Before deploying a coin list, fetch `/v2/products` on the TARGET host and confirm every symbol is `state: "live"` and `contract_type: "perpetual_futures"`. Filter options out by excluding `P-`/`C-` prefixes. Do not assume the demo coin set matches mainnet.

## Order placement procedure

1. **Resolve product.** `GET /v2/products?symbol=<SYM>` on the target host; take the `state == "live"` perpetual. Capture `id` (product_id), `contract_value`, `tick_size`. These are per-symbol and DIFFER across coins — see pitfalls.
2. **Fetch current price.** `GET /v2/tickers/<SYM>` for the live mark/close.
3. **Compute size in contracts.** `size = max(1, floor(risk_usd / (|entry − SL| * contract_value)))`. contract_value scales the per-contract price movement into notional, so sizing WITHOUT it is wrong by orders of magnitude on low-value pairs.
4. **Round prices to tick.** `price = round(round(p / tick_size) * tick_size, 10)`. Sending an unrounded price is rejected or silently fills at the wrong level.
5. **Build body:** `product_id`, `size`, `side` (`buy`/`sell`), `order_type: "limit_order"`, `price`, `stop_loss`, `take_profit`, `reduce_only: false`.
6. **Sign and send** (live mode only) via `POST /v2/orders` with auth headers. Dry-run mode prints the would-be order instead.
7. **Log** the result (order id + state, or DRY-RUN marker).

See `references/order-api.md` for the HMAC signing recipe and a self-contained order builder.

## Safety ladder (escalation order)

1. **Build + dry-run** with placeholder keys: config `trade_enabled` false. Verify endpoints reachable, order payloads correct (size/tick/SL/TP), strategy fires correctly. No orders sent.
2. **Keys in, still dry-run:** paste real testnet keys, keep `trade_enabled: false`. Run and confirm `api_key_set=True` but mode is still DRY-RUN. This catches placeholder-detection bugs before any send.
3. **Live on DEMO:** `trade_enabled: true` + `--live` against the testnet host. Confirm order id + `state` come back. Review PnL on demo.
4. **Mainnet (separate step, only after demo proven):** change ONLY the host in config to mainnet, re-verify products exist on the new host, then `--live`. Never batch the host change with other edits.

## Pitfalls

- **IP whitelist blocks on a dynamic Termux IP — fix is to disable it, not pin it.** Two flavors of the 401 tell you which problem you have:

  1. **`code: ip_not_whitelisted_for_api_key`** (body includes the rejected `client_ip`) — auth/signature are FINE but the key's IP allow-list rejected the source. On Android Termux the egress IP changes on every network switch (WiFi↔mobile data), so pinning the current IP only fails again at the next switch. Correct demo-side fix: in the demo app's API-key settings, clear/disable the IP whitelist (empty list = allow all). The demo key is scoped to testnet play-money so an open whitelist is acceptable; on a real-money mainnet key, pin the IP instead and re-pin when the network changes. Confirm the account is testnet before loosening the whitelist.
  2. **Bare `{"error":"unauthorized","success":false}`** with NO `code` field — this is NOT an IP-block signature. Common causes (check in order): (a) wrong signature format (see pitfall below — query string must be included in the signed message); (b) key revoked or expired; (c) key created with only 'Market Data' scope, no 'Trade' permission; (d) mismatch between demo/mainnet key and host; (e) secret format wrong — try both plain-UTF8 and base64-decoded; (f) key actually IP-blocked but the response was truncated upstream. A bare 401 means re-verify the signature bytes and key scopes before concluding it's a whitelist issue.

**Termux egress IP can rotate through a pool, not just two networks.** On some Termux setups (proxy-based routing) the egress IP changes every 5–20 minutes through a small pool (observed `47.11.96.*` → `47.11.97.*` → `47.11.98.*` → `47.11.99.*` within one session), not only on explicit network switches. Symptom: auth was working, then 401s began without any network change. If the whitelist is empty and 401s still return with `ip_not_whitelisted`, either (a) the demo app UI did not actually save the blank state — go back and re-save explicitly, or (b) a leftover allow-list entry is cached server-side — delete the key and regenerate. Retry loops over 30–40 seconds confirm whether the IP is stable or rotating; if the pool rotates within a single retry batch, no whitelist strategy will work — the whitelist must be fully off. When the block is intermittent, keep the client-side call retry-tolerant but do NOT treat 401 as a transient network error — it is a policy rejection, and retrying will not succeed until the server-side whitelist is fixed.
- **Placeholder key detection: `if api_key:` is a live-fire bug.** A placeholder string like `PASTE_API_KEY_HERE` is truthy, so a bare truthiness check reports "keys set" and will send orders when `trade_enabled` is flipped. Check the value against an explicit placeholder set AND require `len(key) > 10`.
- **`contract_value` differs per symbol — hardcoding breaks sizing.** BTCUSD `contract_value=0.001`, ETHUSD `0.01`, SOL/XRP/ADA `1.0`, DOGE `100`. Size = risk / (price-distance × contract_value); ignore contract_value and a DOGE position is 100× too large. Always read it from `/v2/products` per symbol at order time.
- **`tick_size` differs per symbol — unrounded prices get rejected.** BTC `0.1`, ETH `0.05`, SOL/XRP `0.0001`, ADA `0.00001`, DOGE `0.000001`. Round every price (entry, SL, TP) to the symbol's tick before sending.
- **Testnet demo coin set is a strict subset of mainnet.** A coin list validated on mainnet will silently no-op on demo for the missing symbols. Confirm products on the ACTUAL target host before each run; do not carry the mainnet list into demo expecting it to work.
- **Signature is over METHOD+timestamp+endpoint+body, base64-vs-plain secret matters.** The signature string is `METHOD + timestamp + endpoint + json_body`, HMAC-SHA256 with the API secret, hex-encoded. Most Delta India keys use a plain-text secret (encode to utf-8); some accounts use a base64-encoded secret (decode first). A mismatched interpretation produces `SignatureInvalid` on every request — check the account's key-format setting. **Endpoint in the signature INCLUDES the query string when one is present** — for `GET /v2/positions?contract_types=perpetual_futures` the signed message is `GET{ts}/v2/positions?contract_types=perpetual_futures`. Signing only the bare path on a query-stringed call produces `Signature Mismatch` with `signature_data: "GET{ts}/v2/positions?..."` echoed in the error body (Delta helpfully shows what it expected). Always build the full path+query string first, then sign over that exact string; the request URL must match the signed string byte-for-byte.
- **Demo keys do NOT work on mainnet and vice versa.** A key generated in the demo app is scoped to testnet; sending it to the mainnet host fails auth. Never assume a key travels between hosts.
- **Verify the order actually landed.** A `200` with `success: true` is the signal; capture `result.id` and `result.state`. A `pending` state on a limit order is normal (awaiting trigger); `closed` means filled.
- **5-second signature window.** If a slow fetch or retry pushes send time past 5s from signature time, the request fails with `SignatureExpired`. Regenerate timestamp + signature immediately before the send, not at the top of the cycle.

## Daemon cadence

The daemon runs `run_cycle()` on a fixed interval. For a **1h-bar entry strategy** the fastest useful cycle is **30s** — signals only fire on 1h candle close, so sub-minute cycles add no detection benefit, they only add API load. Public endpoints are throttled per IP on the testnet (~50 req/s burst) and the strategy's per-cycle cost is ~5 requests (4 tickers + 1 candle fetch per coin); at 4 coins the 30s cadence sits at ~8 req/min total, well under limits. **Below 30s on a 1h strategy is wasted work** — signals cannot appear faster than hourly. Faster cycles only make sense if the strategy also uses sub-hour entries (e.g. 5m or 15m bars), in which case match the cycle to the entry timeframe's bar-close rate.

## Verification without keys (build test)

Before any keys arrive, prove the build end-to-end against public endpoints: reach products/tickers/candles on the target host, run the strategy to confirm signals fire, and dry-run the order builder to print the payload (size, tick-rounded prices, SL/TP) for each coin. Confirms the wiring and catches sizing/rounding bugs with zero credential risk. `--live` with placeholder keys must refuse and say so — that refusal IS the safety check.

## Commands

```bash
cd ~/delta_live
python3 delta_live_trader.py            # dry-run (default; never sends)
python3 delta_live_trader.py --live     # sends ONLY if trade_enabled=true AND real keys
# config: ~/delta_live/config.json  (chmod 600, keys here)
# auth:   ~/delta_live/delta_auth.py  (HMAC-SHA256 signing)
# log:    ~/delta_live/trades_live.md  (append-only, IST timestamps)
```

## User preferences captured

- **Hinglish, concise, no restating.** User speaks Hindi/English mixed and wants brief status, not narration.
- **Safety-first escalation:** user explicitly wants demo trading first, mainnet only after. The dry-run→demo→mainnet ladder matches this.
- **User provides keys later, not now.** Build and verify everything keyless first; report ready state; wait for keys. Do not block on missing keys or fabricate placeholders-as-real.
- **Stop before irreversible action.** Never self-promote to mainnet. Confirm before any real-money host change.
- **Never write configs with secrets through shell heredocs.** Delta India API secrets frequently contain `*` characters (and possibly `$` or backticks). An unquoted heredoc like `cat > config.env << 'ENVEOF'` still expands the glob `*` and replaces matches with `**`, silently corrupting the secret before it ever reaches disk — the file has literal `*` where real secret bytes should be, and auth fails with generic 401. Symptom: grep shows `DELTA_API_SECRET=***` (3 chars) where a 45+ char secret was written. Fix: write via Python (`open(...).write(...)`) or the `write_file` tool. Verify length with `len()` after write — if it looks like `[***]{3}` the glob ate it.
- **Never echo secret values even masked.** Reporting `first6/last6` is enough for verification. Full echo into tool args shows up in process listings and logs — that is credential exposure even in demo.

## Files

- `~/delta_live/config.json` — keys + settings, `chmod 600`, placeholders by default
- `~/delta_live/delta_auth.py` — HMAC-SHA256 signing + signed request helper (stdlib only)
- `~/delta_live/delta_live_trader.py` — strategy + order builder, dry-run default
- `~/delta_live/daemon.py` — 24/7 background loop wrapper: single-instance PID lock (`trader.pid`), reloads `config.json` every cycle so `trade_enabled` can be toggled live without restart, runs `run_cycle()` on a fixed interval (300s). Run `python3 -u daemon.py` in background; stop with `kill $(cat ~/delta_live/trader.pid)`
- `~/delta_live/trades_live.md` — append-only action log
- `~/delta_live/HANDOFF.md` — full setup + demo key-acquisition steps
- `references/order-api.md` — signing recipe + order payload builder (copy-paste)

**Signature path is WITHOUT the api-key prefix.** Sign over `METHOD + timestamp + path [+ query] + body` where `path` is the bare endpoint (`/v2/orders`). Delta India does NOT prepend `/{api_key}` to the path for the signature string — that convention is from other exchanges and produces `SignatureInvalid`. The api-key rides in its own HTTP header, never inside the signed message.
