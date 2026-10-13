# Delta v2 Order API — Signing & Payload Builder

Copy-paste reference for authenticating and placing orders. Stdlib only (no requests library — Termux Termux Python 3.14 has it, but these use urllib so they run anywhere).

## Auth signing (HMAC-SHA256)

Signature = HMAC-SHA256 over `METHOD + timestamp + endpoint + body`, secret = API secret, hex-encoded.

```python
import hashlib, hmac, json, time, urllib.request, urllib.parse

def sign(method, path, secret, timestamp, body=""):
    msg = method + str(timestamp) + path + body
    return hmac.new(secret.encode("utf-8"), msg.encode(), hashlib.sha256).hexdigest()

def request(method, host, path, api_key, api_secret, params=None, body=None):
    qs = ("?" + urllib.parse.urlencode(params)) if params else ""
    endpoint = path + qs
    ts = str(int(time.time()))            # generate at SEND time (5s validity)
    body_str = json.dumps(body, separators=(",", ":")) if body else ""
    headers = {"Accept": "application/json", "User-Agent": "HermesTrader"}
    if body:
        headers["Content-Type"] = "application/json"
    headers["api-key"] = api_key
    headers["timestamp"] = ts
    headers["signature"] = sign(method, path, api_secret, ts, body_str)
    req = urllib.request.Request(host + endpoint,
                                 data=body_str.encode() if body else None,
                                 method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())
```

Notes:
- `endpoint` in the signature is the path WITHOUT the host (`/v2/orders`), WITH the query string appended if present.
- For GET requests with query params, sign `path + "?" + query` but the signature body component is empty.
- `timestamp` is Unix **seconds** as a string.
- Most Delta India secrets are plain text (`.encode()`). If the account uses a base64 secret, decode it first: `base64.b64decode(secret)`. Wrong format = `SignatureInvalid` on every call.

## Order payload

```python
body = {
    "product_id": product_id,        # int, from /v2/products
    "size": size,                    # int, in contracts (>=1)
    "side": "buy",                   # "buy" or "sell"
    "order_type": "limit_order",     # "market_order", "limit_order", "stop_market_order", "stop_limit_order", "oco_order"
    "price": price,                  # tick-rounded
    "stop_loss": sl_price,           # tick-rounded, attached SL
    "take_profit": tp_price,         # tick-rounded, attached TP
    "reduce_only": False,            # True for closing/exits only
}
res = request("POST", host, "/v2/orders", api_key, api_secret, body=body)
# res = {"success": True, "result": {"id": ..., "state": "closed"|"pending"|...}}
```

`state` after place: `pending` (awaiting trigger, normal for a limit order off-mark), `closed` (filled).

## Sizing + tick rounding (per symbol)

```python
def rnd(p, tick):                     # round a price to the product's tick_size
    return round(round(p / tick) * tick, 10)

def size_contracts(risk_usd, entry, sl, contract_value):
    per_con = abs(entry - sl) * contract_value   # $ risk per 1 contract
    return max(1, int(risk_usd / per_con)) if per_con > 0 else 1
```

`contract_value` scales price-movement to notional. Per-symbol values (verified): BTCUSD 0.001, ETHUSD 0.01, SOLUSD/XRPUSD/ADAUSD 1.0, DOGEUSD 100. Never hardcode — read from `/v2/products`.

## Public endpoints (no auth, for build-test / product lookup)

```python
# products (filter live perpetuals)
prods = request("GET", host, "/v2/products")
perp = [p for p in prods["result"]
        if p["state"] == "live" and p["contract_type"] == "perpetual_futures"]

# ticker
tr = request("GET", host, "/v2/tickers/BTCUSD")   # tr["result"]["close"]

# candles (resolution is a STRING literal: "1m","5m","1h","1d")
from datetime import datetime, timezone
now = int(datetime.now(timezone.utc).timestamp())
c = request("GET", host, "/v2/history/candles",
            params={"symbol":"BTCUSD","resolution":"1h","start":now-400*3600,"end":now})
# c["result"] = list, time in Unix SECONDS, DESCENDING -> sort ascending before math
```

## Order-side endpoints (auth)

- `POST /v2/orders` — place
- `GET  /v2/orders` — list open orders (`?product_id=` to filter)
- `DELETE /v2/orders` — cancel (body: `[{"id": order_id}, ...]`)
- `PATCH /v2/orders` — edit (cancel+replace)
- `GET  /v2/positions` — open positions (auth)
- `GET  /v2/trades` — trade history (auth)

Cancel signature note: DELETE body is a JSON array; signature body component is the serialized array.

## Dry-run gate (use this shape)

```python
PLACEHOLDERS = {"", "PASTE_API_KEY_HERE", "PASTE_API_SECRET_HERE",
                "your-api-key", "your-api-secret", "changeme", "x"}

def have_keys(k, s):
    return (k or "").strip() not in PLACEHOLDERS and \
           (s or "").strip() not in PLACEHOLDERS and len(k) > 10

def live_mode(args_live, cfg):
    return args_live and cfg.get("trade_enabled") is True and have_keys(cfg.get("api_key"), cfg.get("api_secret"))
```

`--live` without keys/flag must refuse and say why. Never let a placeholder truthiness check pass as "keys set".

## Verified live (no keys) from Termux
- `https://cdn-ind.testnet.deltaex.org/v2/products` → 677 products, 16 live perps
- `https://cdn.india.deltaex.org/v2/products` → 1201 products, 220 live perps
- Tickers + candles work on both, no auth, ~1s per request
- Order payload builder produced correct size/tick/SL/TP for BTC/ETH/SOL/XRP/ADA/DOGE against live testnet prices
