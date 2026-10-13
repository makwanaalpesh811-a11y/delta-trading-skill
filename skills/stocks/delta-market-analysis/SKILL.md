---
name: delta-market-analysis
description: "Delta Market Analysis (multi-TF, win-prob)"
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux]
---

name: delta-market-analysis
description: Analyze Delta India symbol with trend and win probability.
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux, macos]
---
# Delta Market Analysis (multi-TF, win-prob)

## When to use
User asks 'kaha1 ja raha hai', 'win probability', 'market analysis' on a symbol — often from a screenshot of Delta India chart. Trigger words: `analysis`, `win%`, `probability`, `ka data lo`, `kaha ja raha`, or when the user sends a symbol chart screenshot and asks for current direction.

## Fixed output format (user-approved 05-10-2026)
Order and columns are LOAD-BEARING. Do not reorder, do not add emojis beyond the fixed set below.

```
📊 SYMBOL Market Analysis (or — Deep Analysis for expanded mode)
⏰ Time: DD-MM-YYYY HH:MM IST
Last price: $X.XXXX

🎯 Quick View (table):
| Timeframe | Trend | RSI | Signal |
| 5m   | 🟢/🟡/🔴 | X.X  | one-line takeaway |
| 15m  | ...  | ...  | ... |
| 1h   | ...  | ...  | ... |

📈 Detailed (per TF, fixed fields):
- Recent X-minute change %
- Range on TF (open→last)
- ATR (14) as %
- RSI (14) value + label (Overbought >70 / Oversold <30 / Neutral)
- EMA50/EMA200 alignment → 🟢 BULL / 🔴 BEAR / 🟡 MIX
- Up-candle % of last 20

🎯 WIN PROBABILITY (Long):
| Timeframe | Long Win% | Short Win% |
Combined weighted by ATR → one number.

💡 Suggestion: concrete next action given the current chart state (if user is in a position, name Close/Hold/Flip).
```

### Expanded mode (support/resistance levels, use when user asks 'levels' or 'support resistance' or sends multiple screenshots)

Add a **Key Levels** section between Detailed and Win Probability:

```
📍 Key Levels:
- 📌 Nearest Resistance: $X.XXXX  (projected TL break / recent swing high)
- 📌 Resistance R2: $X.XXXX
- 📍 Nearest Support: $X.XXXX  (recent swing low)
- 📍 Support S2: $X.XXXX
```

Use pivot-highs/lows with pl=3, pr=3 from `delta-market-analysis` logic; pick nearest level ABOVE `last` for R1, nearest BELOW for S1, then next-nearest for R2/S2. Never reuse the same level on both sides.

**User-approved the base format as `Good ye message formet acha tha`** — do not drop sections, do not add new emoji beyond the set above, do not switch to a different language.

## Data flow
1. `vision_analyze` the screenshot if provided — extract symbol, current position side, TP/SL levels if visible. Never trust a screenshot's numbers over the API; API wins.
2. Hit `https://api.india.delta.exchange/v2/history/candles?resolution=<tf>&symbol=<SYM>&start=<now-bars*sec>&end=<now>` with `User-Agent: Mozilla/5.0`. Parse `result[]`, sort by `time` ascending, drop the forming candle (`time + sec > now`).
3. Fetch **all three TFs: 5m, 15m, 1h** with bars=500 each. One fetch per TF, not one big fetch — TF-specific ATR/RSI/EMA must be computed on the TF's own candles.
4. Compute per TF:
   - Change on last 10 bars (5m view), 30 bars (15m view), 60 bars (1h view).
   - Total range open[0]→close[-1] %.
   - ATR(14) Wilder smoothing → `atr/last*100`.
   - RSI(14) Wilder smoothing.
   - EMA50 and EMA200 on close; if `E50>E200 AND close[-1]>E50` → BULL; mirror for BEAR; else MIX.
   - Up-candle fraction: `sum(diff(c)>0 in last 20) / 20`.
5. Win prob per TF (fixed thresholds, do NOT re-derive):
   - RSI<30 → Long 75% (oversold bounce)
   - RSI>70 → Long 25% (overbought)
   - RSI<45 → Long 55%; RSI>55 → Long 45%; else 50%.
   - Adjust by trend flag: BULL adds +5 to Long, BEAR adds +5 to Short, MIX neutral.
   - Adjust by up-candle fraction on last 20: >55% tilts to Long, <45% tilts to Short, ±5 each.
6. Combined win% = ATR-weighted average across 5m/15m/1h (higher ATR = higher weight). Report as a single integer.

## Pitfalls
- **Screenshot is not the source of truth.** User's screenshot can be stale or from a different TF. Always re-fetch 5m/15m/1h from API before answering; the API is the ground truth and only source allowed for win%.
- **Do not invent a win% number without a threshold rule.** If RSI is missing or the number looks made up, that is fabrication — either compute RSI properly or say 'insufficient data'.
- **Do not compute RSI on 5m bars then reuse on 1h.** Every TF has its own candles and its own RSI/ATR/EMA. Reusing indicators across TFs silently breaks the analysis.
- **Do not present one directional call across all TFs as if consistent.** If 5m is BEAR and 1h is BULL, name the conflict and give the user the tradeoff — not a single 'BUY' verdict. Contradictions are the finding, not noise.
- **Drop the forming candle.** Delta returns the currently-in-progress candle; including it biases RSI/ATR toward an unstable bar. Filter `time + sec <= now`.
- **Delta India may return a forming candle with `close=0` on some endpoints.** When the API returns a row where `close` is 0 (or missing), Wilder-smoothed RSI/ATR/EMA all break (RSI returns 100, ATR returns `inf`). Filter rows to `close > 0` BEFORE converting to numpy, otherwise downstream math silently produces `nan`/`inf` and the analysis prints `NaN%` or crashes on `sr_above.min()`. The `time + sec > now` check alone is NOT sufficient — use both filters.
- **Some timeframes are unavailable on Delta India.** E.g. `4h` returned empty `result` while `1h` worked. If `len(rows) == 0`, either drop that TF from the analysis or fall back to `1h` — never present empty/zero rows as a live signal.
- **IST time = UTC+05:30 = +18000s.** `time.strftime('%H:%M', time.localtime(time.time()+18000))`.
- **Do not recommend a trade size, leverage, or entry price from this analysis alone.** The skill produces direction and probability only. Order sizing belongs to `paper-trade-simulator` / `delta-live-order-execution`.
- **Delta India requires USD-suffixed symbols.** `PENDLEUSD`, not `PENDLE`. If the API returns an empty `result`, first try the USD-suffixed form.

## Reusable snippet
```python
import json, urllib.request, urllib.parse, time, numpy as np
BASE='https://api.india.delta.exchange'
TF={'5m':300,'15m':900,'1h':3600}
def fetch(sym, tf, bars=500):
    sec=TF[tf]; now=int(time.time())
    q=urllib.parse.urlencode(dict(resolution=tf,symbol=sym,start=now-bars*sec,end=now))
    req=urllib.request.Request(f'{BASE}/v2/history/candles?{q}',headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=20) as r: rows=json.load(r).get('result') or []
    rows=[x for x in rows if x['time']+sec<=now]
    return dict(o=np.array([float(x['open']) for x in rows]),h=np.array([float(x['high']) for x in rows]),l=np.array([float(x['low']) for x in rows]),c=np.array([float(x['close']) for x in rows]))
```
Extend with `wilder_atr(h,l,c,n=14)`, `wilder_rsi(c,n=14)`, `ema(a,n)` — all Wilder-smoothed, not simple SMA.

## Verification checklist (before answering)
- [ ] Symbol has `USD` suffix in the API request.
- [ ] Fetching returned non-empty rows for all three TFs.
- [ ] RSI/ATR computed on each TF's own candles.
- [ ] Trend flag derived from EMA50/EMA200, not eyeballed from the chart.
- [ ] Combined win% is ATR-weighted, not the max or the mode.
- [ ] Output follows the fixed format above (table rows, section headers, emoji set).
- [ ] If user is in a visible position (from screenshot), Suggestion section names Close/Hold/Flip with reason — not a generic 'consider caution'.
