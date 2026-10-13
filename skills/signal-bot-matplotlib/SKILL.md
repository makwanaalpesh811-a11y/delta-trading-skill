---
name: signal-bot-matplotlib
description: "Signal Bot (matplotlib variant)"
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux]
---

name: signal-bot-matplotlib
description: Use for ~/signal_bot.py — matplotlib Delta bot.
metadata:
  hermes:
    tags: [trading, telegram, matplotlib, signal-bot, delta-india]
    category: devops
    related_skills: [tredalgo-signal-bot, paper-trade-simulator, telegram-standalone-bot]
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux, macos]
---

# Signal Bot (matplotlib variant)

Two versions coexist in the same directory:

- **V1 (FROZEN)**: `~/signal_bot.py` → `/sdcard/Hermes_Almari/01_STRATEGY/code/signal_bot.py`. 49 coins, EMA300 default params, matplotlib PNG, Telegram sendPhoto. Trigger word `algo`. User explicitly said `Algo v1 save kar lena us me koy chenj nahi hoga` — **do not modify V1**. It may be running as a background loop.
- **V2 (ETH Multi-TF)**: `/sdcard/Hermes_Almari/01_STRATEGY/code/signal_bot_v2.py`. Reads pre-aggregated M1/M3/M15 candles from `/sdcard/Hermes_Almari/02_DATA/eth_m{1,3,15}_candles.csv` (337K / 112K / 22K rows, Jan–Aug 2026, built by `build_eth_m1.py` from ticks then `build_eth_multi_tf.py` from M1). Same strategy engine as V1 (EMA300 + Trendline + Swing-2). **Scans all 3 TFs, merges signals sorted by timestamp across TFs.** Sends **2 photos per trade** (entry-only, then SL/TP overlay). Current scan: 5795 signals (4077 M1 + 1424 M3 + 294 M15). `~/trade_analyzer.py` post-checks whether SL or TP hit for a given trade index.

**V2 state now carries TF tag on every signal.** Each signal dict has `"tf": "1m"|"3m"|"15m"`. Photo filenames include TF: `trade_002_3m_entry.png`. Captions include TF: `ETHUSD | 3m | 01 Jan 2026 06:26 IST`. `get_current_trade()` loads the correct TF's data file on demand — do not pre-load all 3 TFs into memory.

**M1 → M3/M15 aggregation uses pandas resample**, not manual numpy bucketing (which had empty-slice bugs). Canonical aggregator is `~/build_eth_multi_tf.py`:
```python
agg_df = df.set_index("dt").resample(f"{minutes}min", closed="left", label="left").agg(
    open=("open","first"), high=("high","max"), low=("low","min"),
    close=("close","last"), volume=("volume","sum")
).reset_index()
```
Filter empty buckets: `agg_df[agg_df["open"] > 0]` before saving. Convert back to unix seconds: `time = dt.astype(np.int64) // 10**9`.

Different from `tredalgo-signal-bot` (Pillow-based Pine-style). Both V1 and V2 use ★ BLACK STAR (U+2605) for backtested coins (U+2605 renders fine in DejaVu; U+2B50 does not).

## When to use
- Editing strategy params, WATCH list, or Telegram delivery.
- Adding/removing coins or timeframes.
- Rendering charts (`draw()` function, matplotlib backend).
- Deploying as background process for 24/7 signal alerts.
- Debugging signal detection (`check_signal()`, `add_indicators()`), env/token loading.

Do NOT use for Pillow-based `tredalgo_signal_bot.py` (`tredalgo-signal-bot` skill). Do NOT use for paper-trade engine (`paper-trade-simulator`).

## User trigger: `algo`

Word `algo` in a chat message = turn bot ON in background. Command:

```bash
nohup python3 ~/signal_bot.py algo > ~/signal_bot.log 2>&1 &
```

STOP: `pkill -f signal_bot.py`. Status: `pgrep -f signal_bot.py && echo ON || echo OFF`.

On startup prints:
```
🟢 ALGO BOT ON  (token=<first-10>... chat=<chat_id>)
   WATCH: <N> symbols, SLEEP=<N>s
```

## Token / credentials

- Stored at `~/.signal_bot_env` (auto-loaded via `os.environ.setdefault`). Format:
  ```
  TG_TOKEN=123456:ABCdef...
  TG_CHAT_ID=8167438970
  ```
- Bot identity: `@alpeshalgobot` "Tred with alpesh", id 8077800501.
- Verify with `GET /getMe` before sending — 404/401 means token invalid.
- Never paste the token into a chat. If Hermes redacts it as `8077800501:***` on disk, that's expected.

## WATCH list structure

```python
WATCH = [
    # ⭐ Grid backtest winners (9 coins)
    ("ETHUSD",  "1h"), ("BTCUSD",  "1h"), ("SOLUSD",  "1h"), ("XRPUSD",  "1h"),
    ("BNBUSD",  "1h"), ("DOGEUSD", "1h"), ("ADAUSD",  "2h"),  # grid WINNER PF 2.06
    ("AVAXUSD", "1h"), ("LINKUSD", "1h"),
    # ✦ 40 new coins (verified present on Delta India)
    ("TRXUSD","1h"), ... ("ZROUSD","1h"),
]
BACKTESTED = {"ETHUSD", ..., "LINKUSD"}
def star(sym): return "★" if sym in BACKTESTED else ""
```

`star()` returns ★ prefixed to symbol name; used in `caption()` and the top-title text of `draw()`.

**Delta India symbols ALL require `USD` suffix** — bare `ETH`/`LINK`/`TRX` return 0 candles. Verified present (49 total): ETHUSD, BTCUSD, SOLUSD, XRPUSD, BNBUSD, DOGEUSD, ADAUSD, AVAXUSD, LINKUSD, TRXUSD, DOTUSD, LTCUSD, UNIUSD, NEARUSD, APTUSD, ARBUSD, OPUSD, FILUSD, HBARUSD, ETCUSD, BCHUSD, AAVEUSD, DYDXUSD, SUSHIUSD, ZECUSD, DASHUSD, SUIUSD, SEIUSD, TIAUSD, JUPUSD, LDOUSD, STXUSD, ARUSD, XLMUSD, XMRUSD, AXSUSD, MANAUSD, ENJUSD, GALAUSD, RUNEUSD, PENDLEUSD, KSMUSD, GLMUSD, TAOUSD, WIFUSD, ORDIUSD, LAYERUSD, API3USD, ZROUSD. Missing (0 candles): MATICUSD, ATOMUSD, VETUSD, EGLDUSD, ALGOUSD, KAVAUSD, XTZUSD, SANDUSD, GRTUSD, COMPUSD, SNXUSD, CRVUSD, MKRUSD, ENSUSD, ONEUSD, UMAUSD, GNOUSD, ICPUSD, IMXUSD, FTMUSD, FLOWUSD, NEOUSD, EOSUSD, QTUMUSD.

## Strategy params (default)

```python
a = NS(pl=3, pr=3, ema=300, atr_len=14, atr_mult=2.0, rr=2.0,
       side="both", max_age=0)
```

- `pl=3, pr=3`: pivot L=3 left bars, R=3 right bars confirmation.
- `ema=300`: EMA length for trend filter.
- `atr_mult=2.0`: SL = ATR(14) × 2.0.
- `rr=2.0`: TP = entry ± 2 × risk.

Grid WINNER combo (higher PF): `ema=100, atr_mult=1.0, rr=3.0, pl=5` on `ADAUSD 2h` — PF 2.06, +40.86R/yr. Switching requires changing `a` AND WATCH entry for ADAUSD to `2h`.

## Modes

| Arg | Behavior |
|-----|----------|
| `ping` | Telegram test message (validates token) |
| `dry` | Check latest closed candle, local photo, no Telegram |
| `dry-latest` | Walk back 1000 candles for latest signal, local photo |
| `algo` | Bot ON (loop, 60s interval, Telegram sends) |
| `once` / no arg | Single check + Telegram send |

## V2 photo flow (2 photos per trade, no phase 3)

User-specified: V2 sends **exactly 2 photos** per trade — entry only, then entry+SL/TP overlay. No live-tracking phase; `next` advances to the next trade's Phase 1.

Implementation uses a `draw(D, S, symbol, out, trade_num, mode=...)` parameter:

- `mode="entry"` — candles, EMA, swing markers, trendline, entry candle only. SL/TP zones, horizontal SL/TP lines, and SL/TP rows in the bottom info box are all suppressed.
- `mode="sltp"` — same chart plus SL/TP zones + horizontal SL/TP/entry lines + full trade-plan info box.
- `mode="full"` — same as `sltp` (kept for backward compat).

When `mode="sltp"`, SL/TP zones must be **obviously visible**, not subtle:
- Zone width ≥ 1.5× the PAD (do NOT use `PAD - 2` — that made the user say "lagne wala malum nahi pad raha").
- Alpha ≥ 0.30, edge linewidth ≥ 2.5.
- Add solid horizontal SL and TP lines extending from `t-2` to `t+w`, plus a dashed yellow entry line. Without these, users cannot tell which price the level is at.

State file `~/signal_state_v2.json` holds `{signals, current_idx, total_signals}` — `next` increments `current_idx`. `send` / `photo` / `next` all generate BOTH photos and send them as two consecutive `sendPhoto` calls with distinct captions ("Photo 1 of 2 — entry only" / "Photo 2 of 2 — full trade plan").

## ETH Multi-TF data pipeline (V2)

V2 does NOT hit the Delta India API live. It reads pre-aggregated candle CSVs.

**Build once (2-step):**
```bash
python3 ~/build_eth_m1.py          # ticks → M1 (~15 min, one-time)
python3 ~/build_eth_multi_tf.py    # M1 → M3 + M15 (~5s)
```
- `build_eth_m1.py` reads `/sdcard/Hermes_Almari/02_DATA/backtest_data/extracted/ETHUSD_2026-*.csv` (53M ticks, 8 monthly files ~2.8 GB) → `eth_m1_candles.csv` (337K rows, 16 MB).
- `build_eth_multi_tf.py` reads `eth_m1_candles.csv` → `eth_m3_candles.csv` (112K rows, 5.4 MB) + `eth_m15_candles.csv` (22K rows, 896 KB). Uses pandas resample — do not re-implement with numpy bucketing (empty-slice bugs on first iteration).

**Scan all signals across 3 TFs:**
```bash
python3 ~/signal_bot_v2.py scan
```
Loads 1m+3m+15m, runs `find_all_signals()` per TF, merges results sorted by `t` (unix timestamp) across all TFs. Each signal carries `"tf"` tag. Saves to `~/signal_state_v2.json` with `current_idx=0`.

**Send/advance:**
```bash
python3 ~/signal_bot_v2.py send   # send BOTH photos of current trade
python3 ~/signal_bot_v2.py next   # advance current_idx, print next trade
python3 ~/signal_bot_v2.py dry    # render both photos locally, no send
python3 ~/signal_bot_v2.py ping   # token check
```

**Analyze a trade's outcome** (post-hoc SL/TP hit check against M1 data):
```bash
python3 ~/trade_analyzer.py <trade_num>   # single trade result
python3 ~/trade_analyzer.py summary 5000  # win/loss/PnL across N trades
```
Writes `~/trade_results_summary.json`. PnL formula is direction-aware: LONG `pnl=(exit-entry)/entry*100`, SHORT `pnl=(entry-exit)/entry*100`. SL for short sits ABOVE entry, SL for long sits BELOW entry.

## Deploy

Background with `terminal(background=true)` — do NOT use `nohup ... &` inline (Hermes terminal rejects shell-level background wrappers). Log: `~/signal_bot.log` (V1) or `~/signal_bot_v2.log` (V2). Dedup via `~/signal_state.json` (V1) / `~/signal_state_v2.json` (V2) — same signal bar_time isn't re-sent. Delete state file to force resend.

To start V1: `terminal(background=true, command="python3 ~/signal_bot.py algo")`. To stop: `pkill -f signal_bot.py`. V2 is state-driven (no loop) — drive it via `send` / `next` commands, not `algo`. To stop only V1 while leaving V2 state intact: `pkill -f signal_bot.py` (V2 has no background process).

**Redacted-token fallback**: if on-disk token shows `8077800501:***`, test scripts must read from `~/.signal_bot_env` or accept `TG_TOKEN=...` env var at call time.

## Pitfalls

**⭐ emoji glyph missing in DejaVu Sans**: matplotlib renders ⭐ (U+2B50) as a box-with-X because DejaVu Sans lacks the emoji codepoint. Use ★ (U+2605, BLACK STAR) instead — DejaVu Sans supports it. Verify by rendering a test image and vision_analyze; if you see a missing-glyph box, switch glyph.

**Matplotlib install on Termux**: `pip install matplotlib` can hang >5 min on Termux aarch64 (kiwisolver build). Use `pkg install -y matplotlib` — pulls a Termux-native build with pre-built kiwisolver wheel. Confirmed working: mpl 3.11.2. If pip install does run, do NOT kill it mid-way with timeout — run in background with `notify=true`.

**Delta India symbol naming**: bare `ETH`, `LINK`, `TRX` return 0 candles. All must be suffixed `USD`. The Markets endpoint (`/v2/exchange/markets`) returns 404 — verify symbols by hitting `/v2/history/candles?symbol=X&resolution=1h&start=...&end=...` and checking `len(result) > 0`.

**Forming candle filter**: `fetch_candles()` filters out candles where `x["time"] + sec > now` — otherwise the in-progress candle shifts the signal by one bar. Skipping this produces signals that don't reproduce on the confirmed bar.

**Dedup across restarts**: `signal_state.json` maps `symbol|tf` → last sent bar_time. If the bot restarts mid-cycle, an already-sent signal won't re-send.

**Env auto-load order**: `signal_bot.py` reads `~/.signal_bot_env` BEFORE reading `os.environ` for `TG_TOKEN`/`TG_CHAT_ID`. Uses `setdefault`, so shell env overrides file. If `export TG_TOKEN=***` fails in chat, check the file — that's the source of truth.

**Almari symlink**: physical files live under `/sdcard/Hermes_Almari/01_STRATEGY/code/`; `~/signal_bot.py`, `~/signal_bot_v2.py`, `~/build_eth_m1.py`, `~/trade_analyzer.py` are all symlinks. Moving a physical file requires `ln -sf <new-path> ~/<name>`. Same for `~/.signal_bot_env` and `~/bt_cache/` — all symlinks to `/sdcard/Hermes_Almari/`.

**PnL direction bug**: for SHORT, PnL is `(entry - exit)/entry * 100`, NOT `(exit - entry)`. A naive `(exit-entry)` formula flips the sign on every short — losses look like wins and vice versa. Same for TP/SL checks: for SHORT, SL is hit when `high >= sl` and TP when `low <= tp`; for LONG, SL when `low <= sl` and TP when `high >= tp`. Both must be checked even if the other is hit first, to determine which came first.

**Telegram sendPhoto timeout**: sending two photos back-to-back in one Python process can exceed the default 40s `urllib` timeout (each `sendPhoto` is 20-30s on Termux due to file upload). Set `urlopen(timeout=60)` minimum in the multi-photo loop, or the second `sendPhoto` will silently fail with a socket timeout after the first succeeds. If the first send succeeded but the second timed out, re-run only the second send (the state is unchanged) — do NOT re-run `send` from scratch, that would double-send the entry photo.

## Verify after edits

1. `python3 -m py_compile ~/signal_bot.py` — syntax.
2. `python3 -c "import signal_bot as sb; print(sb.BOT_TOKEN[:12], sb.CHAT_ID)"` — env auto-load works.
3. `python3 ~/signal_bot.py ping` — Telegram token valid.
4. `python3 ~/signal_bot.py dry-latest 2>&1 | head -20` — data fetch + indicator + signal + render all work, glyph renders (no box-X warnings).
5. `pgrep -f signal_bot.py` — background deploy check.
