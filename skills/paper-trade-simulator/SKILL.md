---
name: paper-trade-simulator
description: "Paper-Trade Simulator"
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux]
---

name: paper-trade-simulator
description: Use for 24/7 crypto paper-trade simulator on Termux. Trigger word 'tredalgo' or 'trading algo' = v1 setup.
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux, macos]
---

# Paper-Trade Simulator

Long-running process that simulates a crypto strategy against live market data on Termux. Read-only, no orders, no credentials. Runs in a dedicated Termux Session 2 as a single-screen terminal dashboard with in-place clear+redraw every 1 second (Binance live prices + Delta 1h candles for signals); persists trade records to a CSV the user can view anywhere.

## TREDALGO v1 + v2 — current running state

**Trigger word:** When user says `tredalgo`, `trading algo`, `paper trade`, `sim chala` — auto-load this skill + do `skill_view(name='paper-trade-simulator')` + check sim status via `pgrep -af terminal_dashboard` and `cat ~/paper_trade/state.json` + `cat ~/paper_trade/state_v2.json`. Assume v1 + v2 unless user says otherwise.

### TREDALGO v1 — FROZEN (Sep 25 20:24 IST)
- **File:** `~/paper_trade/terminal_dashboard.py` (running) AND backup `terminal_dashboard_v1.py`
- **State:** `~/paper_trade/state.json` (1s refresh)
- **CSV:** `/sdcard/Hermes_FFiles/paper_trades.csv` (append-only)
- **Lock:** `~/paper_trade/.lock`
- **Launch Session 2:** `cd ~/paper_trade && termux-wake-lock && python3 -u terminal_dashboard.py`
- **UI:** colored PnL (green/red), inline trendline per coin (TL_UP=green, TL_DN=red), entry time MM-DD HH:MM per row, L=green/S=red
- **Strategy:** EMA300+Pivot(3,3)+ATR14×2 SL+RR 2.0+1h, close-confirmed signals only, live Binance entry, Delta 1h candles every 60s
- **Coins:** BTCUSD, ETHUSD, XRPUSD, SOLUSD, LINKUSD, INJUSD, AAVEUSD
- **Capital:** $10k per coin = $70k total
- **Status:** RUNNING since 20:53 IST. **DO NOT MODIFY** — frozen per user request Sep 25. Any future change goes into v2, not v1.
- **v1 state after 20:35 reset:** fresh $70k, no prior positions/trades. CSV deleted at reset, recreated when first trade closes.

### TREDALGO v2 — CURRENT DEPLOY MODE (Sep 26 2026)

**Status:** v2 RUNNING as of 09:23 IST 26 Sep. State fresh (`started_at` 2026-09-26T03:53:52Z). 12 LONG positions opened on bottom_1h, all at entry_t ~1790394848 (09:23 IST). No trades closed yet at that snapshot. v1 also running with 4 LONG positions (SOLUSD, LINKUSD, AAVEUSD, +1) on `COINS` list. Code updated 26 Sep with fixed 25-coin deploy list + live cross detection (was close-confirmed bar-close entry) + aggressive grid-optimized params. Previous multi-TF experiment (killed 08:35 IST 25 Sep) is history.

**Current deploy config (grid-backtest-driven, AGGRESSIVE):**
- **Strategy:** EMA300 + Pivot(3,3) + ATR14×**1.5** SL + RR **3.0**, live cross detection (NOT close-confirmed)
- **Coins:** 25 fixed (backtest top-25 by R on 1h)
- **Timeframes:** 1h ONLY (15m disabled — 15m backtest was -1009R vs 1h -130R; 15m NOT better than 1h for this strategy, opposite of the v2 experiment prediction)
- **Capital:** $15k total = $600/coin (per_slot = $15k / 25 coins × 1 TF). 1% risk per trade = $6.
- **Files:** `~/paper_trade/terminal_dashboard_v2.py`, `~/paper_trade/state_v2.json`, `/sdcard/Hermes_FFiles/paper_trades_v2.csv`, `~/paper_trade/.lock_v2`
- **Launch (Session 2):** `cd ~/paper_trade && termux-wake-lock && python3 -u terminal_dashboard_v2.py`
- **Recovery:** `pkill -f 'python3 -u terminal_dashboard_v2.py'`; `rm -f ~/paper_trade/.lock_v2 ~/paper_trade/state_v2.json`

**Deploy list (1h top-25, filter: R≥30, %W≥35, n≥150):**
`MEUSD, SUNUSD, WLDUSD, MOVEUSD, NEARUSD, ZECUSD, SONICUSD, METAXUSD, ENAUSD, BLURUSD, REDUSD, VVVUSD, TRUMPUSD, EVAAUSD, BIOUSD, BERAUSD, RIVERUSD, JTOUSD, INJUSD, TIAUSD, STXUSD, HUSD, TRXUSD, BEATUSD, UNIUSD`

Top performers by R: MEUSD +69.8R, SUNUSD +67.0R, WLDUSD +53.4R, MOVEUSD +51.5R, NEARUSD +48.3R, ZECUSD +47.9R, SONICUSD +47.6R. Total 25-coin 1h net: $+101,000 over ~5 months.

**Binance/Delta coverage gap:** 18/25 coins on Binance USDT. 7 not on Binance: SONIC, METAX, VVV, EVAA, RIVER, H, BEAT. v2.py has Delta fallback wired in both `_parallel_signals` and `update_monitor_live_prices` — Binance first, Delta fallback for missing. All 25 exist on Delta India products.

**Code changes applied (26 Sep):**
- Added `MONITOR_FIXED_LIST = [...25 coins...]` + `TIMEFRAMES_ENABLED = ["1h"]`; `TIMEFRAMES = TIMEFRAMES_ENABLED` (was hardcoded list of 5)
- `update_monitor_list()` uses fixed list when set (skips Binance discovery)
- `_parallel_signals` falls back to Delta when Binance returns <210 candles or fails
- `update_monitor_live_prices` fetches last 1h candle from Delta for coins missing on Binance
- Capital math unchanged: `per_slot_capital = BOTTOM_COINS_CAPITAL / n_coins`; total across `TIMEFRAMES` = `BOTTOM_COINS_CAPITAL × len(TIMEFRAMES)`
- Entry logic replaced: `process_live_cross_check` runs every cycle (live price vs cached EMA300 + dn/up trendline), tracking `_last_cross_dir` per coin. Enter only on FRESH cross (prev=None, current=sig). Setup must BREAK + REFORM before re-entry after exit. Session-start reset clears `_last_cross_dir=None` so first cross after launch counts as fresh.

**Grid backtest result (26 Sep, top-25 1h, applied to v2):** RR=3.0 dominates across all SL values. Best raw R: SL=1.0 RR=3.0 (+1475R, 30% W, 56% DD — brutal, not deployed). **DEPLOYED combo: SL=1.5 RR=3.0 R=1%** — +1415R, 30% W, 8.1% DD, lev≈9.6x, PnL=$+155k (aggressive per user request). Best risk-adjusted (not deployed): SL=2.0 RR=3.0 R=0.5% (+1143R, 2.6% DD, R/DD=448). V1 frozen baseline (SL=2.0 RR=2.0 R=1%) = +1116R, 5.5% DD, lev≈7.7x. Full analysis in `references/grid-backtest.md`.

**Backtest data (source for deploy decision):**
- 220 coins fetched from Delta, 5-6 months history
- 1h: 73,277 trades, 34.6% W, net -$129,635 across all coins; 86/219 coins profitable (39%)
- 15m: 163,753 trades, 36.2% W, net -$1,009,227; only 35/218 coins profitable (16%)
- Result: 15m churn destroys value 8× worse than 1h. Long-TF is still better, but 15m is NOT better than 1h. The v2 experiment prediction ("longer TF = better W") was wrong for 15m vs 1h; correct only for low-TFs (1m/3m/5m).
- Full results: `~/paper_trade/backtest/results.json`, `15m_percoin.csv`, `1h_percoin.csv`, `deploy_list.csv`

**Multi-TF experiment mode (historical, was the default 25-26 Sep):**
- 200 monitor coins × 5 TFs (1m/3m/5m/15m/1h), $15k per TF = $75k total
- Separate state dict per TF: `bottom_1m`, `bottom_3m`, etc.
- Same coin = 5 positions max (1 per TF), max $750 risk per coin
- Purpose: measure which TF wins. Result: 1m/3m/5m all sub-30% W, 15m too few trades to conclude, 1h produced zero close-confirmed signals in 23h. Confirmed "longer TF better" pattern only for very low TFs.
- 23h results: 495 trades, -$768.64 (-1.0%) on $75k, 336 positions still active

**Both v1 + v2 can run simultaneously** — separate state files, locks, CSVs. Requires two Termux sessions or tmux.

### Version history
- v0 (pre-Sep 24): legacy MD/HTML dashboards — rejected
- v1 (Sep 25 20:24): terminal clear+redraw 1s, colored PnL, inline trendline, entry time — **FROZEN**
- v2 (Sep 25 23:08 – Sep 25 08:35): top=v1 same + bottom = 101 coins × 5 TFs experiment mode (all TFs trade simultaneously, separate state dict per TF, $75k total capital) — **HISTORY**. 23h data confirmed 1m/3m/5m bleed via churn, 15m too few trades to conclude, 1h produced zero close-confirmed signals in that window.
- v2 (Sep 26 09:00+): DEPLOY MODE — fixed 25-coin list (1h top by R, backtest R≥30/%W≥35/n≥150), TIMEFRAMES=["1h"], live cross detection every cycle (replaced close-confirmed bar-close entry). Binance/Delta fallback wired for 7 coins not on Binance.
- v2 (Sep 26 ~14:00 IST): AGGRESSIVE PARAMS — grid backtest (2500 runs × 25 coins × 11-16mo) showed RR=3.0 dominates across all SL values. Applied atrMult=1.5 + rr=3.0 (was 2.0/2.0). ~9.6x effective leverage. +27% R at 1.5× DD vs v1 params. Backup: `terminal_dashboard_v2.py.bak.20260926_112041`.

### Recovery from any version
```bash
# v1
pkill -f terminal_dashboard_v1.py   # or pkill -f "terminal_dashboard.py" without _v1
rm -f ~/paper_trade/.lock ~/paper_trade/state.json
# v2
pkill -f terminal_dashboard_v2.py
rm -f ~/paper_trade/.lock_v2 ~/paper_trade/state_v2.json
# CSVs kept (persistent history) — only clear on explicit reset request
```

**Note:** `pkill -f terminal_dashboard.py` will match BOTH v1 and v2 filenames (substring match). Use `pkill -f terminal_dashboard_v1.py` / `pkill -f terminal_dashboard_v2.py` for safety, or `pkill -f "terminal_dashboard.py"` for v1 (which won't match v2 because v2 filename has `_v2` suffix).

---

## Always-on rules

- **UI: terminal, `os.system('clear')` + `print` + `sys.stdout.flush()` — for clear/refresh ONLY. ANSI COLOR codes ARE OK and DESIRED for PnL direction + trendline direction. NOT ANSI cursor-home / clear / alt-screen codes. NOT browser, NOT MD append log.** User rejected browser/HTML ("braujer nahi chahiye") and MD append ("print ke niche print ka loop nahi"). On Termux specifically, ANSI cursor-manipulation codes (`\x1b[H`, `\x1b[2K`, `\x1b[?1049h`, `\x1b[J`) do NOT render — they print as literal escape text and leave ghost/partial rows. `os.system('clear')` is the only reliable clear in Termux. Correct loop: `os.system('clear'); print(dashboard_str); sys.stdout.flush(); time.sleep(...)`. The apparent blink user complained about was from a 1s cycle hitting a slow fetch (Delta API ~500ms), not from `os.system('clear')` itself — at 1s refresh with Binance-only live prices the clear is invisible. Do NOT use ANSI cursor-home on Termux; it produces garbled output ("sreen me content overlap"). **BUT ANSI color codes ARE rendered correctly by Termux** — user explicitly requested green=up/profit, red=down/loss. Define `GREEN="\x1b[32m"; RED="\x1b[31m"; BOLD="\x1b[1m"; DIM="\x1b[2m"; RESET="\x1b[0m"` and wrap PnL / direction / trendline text: `color_pnl(v, s) = f"{GREEN}{s}{RESET}" if v>=0 else f"{RED}{s}{RESET}"`. Trendline `TL_UP` wrapped in GREEN, `TL_DN` wrapped in RED. Long/short: LONG in GREEN, SHORT in RED.
- **Two-session workflow is the default.** Session 1 = coding, status checks, edits. Session 2 = dashboard running full-screen. The sim must be a normal foreground `python3` process the user launches in Session 2, not a Hermes-spawned background process. Give the user a single-line launch command they paste into Session 2; do not try to spawn it from Session 1. **If the user has one termux session and wants the dashboard to survive screen-lock, use `tmux`**: `tmux new -s trade` → run dashboard → `Ctrl+B D` to detach → `tmux attach -t trade` to re-attach. Tmux is preferred to a second Termux session when the user is running short on sessions.
- **Read-only data.** Public REST only: Binance `/api/v3/ticker/price` for live prices, Delta `/v2/history/candles` for 1h entry signals. Never set `DELTA_MCP_MODE=trade`, never put API keys in env, never place orders. All "trades" are simulated against a cash-equity ledger.
- **No fabricated data.** Every equity number must come from an API candle or ticker that actually arrived. If the API fails, log the failure and skip — do not use stale bars.
- **State is append-only JSON.** `state.json` gets overwritten with the latest snapshot; the trade history inside it is append-only. Never truncate a coin's trade list.
- **Dashboard files are overwrite.** HTML dashboards overwrite the same file every cycle (so the browser auto-refresh shows current state). Only event logs are append-only. Do not mix modes: pick append (event log) OR overwrite (dashboard), not both for the same file.
- **Two-tier API architecture (current).** Binance API for live prices (every 1s, ~100ms, free, no key). Delta API for 1h candles only (every 60s, entry signals). This is the ONLY way to achieve 1s refresh: Binance gives real-time prices instantly; Delta is slow (~500ms per call) and is only called every 60s for signal updates. Exits checked against live Binance price every 1s. Entries evaluated on 1h closed bars from Delta, cached and reused.
- **Session-start gate.** When the process launches (even if state persists), `session_start_t = int(datetime.now(timezone.utc).timestamp())` and cached signals are cleared (`signal_dir=None`, `signal_valid_t=None`, `_last_cross_dir=None`, `last_entry_bar_time=None`) for every coin across every TF. Rationale: user rule "session start hone ke baad new signal bane wahi trade ho" — do NOT enter on pre-session cached signals. Existing positions survive the reset (they'll close via SL/TP as normal); only entries are gated by the new `session_start_t`.
- **v2 entry = live cross detection (not close-confirmed).** Each cycle, current live price vs cached EMA300 + trendline determines setup state: `sig = 1` if `live > EMA300 AND live > dn_line_now`, `-1` if `live < EMA300 AND live < up_line_now`, `None` otherwise. Track `_last_cross_dir` per coin across cycles. Enter ONLY on a FRESH cross — previous cycle's `_last_cross_dir` was `None` (not in setup) AND current cycle is non-`None` (in setup). During position: keep tracking `_last_cross_dir` so that post-exit, the setup must BREAK and REFORM before another entry — no immediate re-entry on the same setup. Implementation: `process_live_cross_check(state, prices)` runs every cycle, alongside `process_exit_check`. Live prices for monitor coins are refreshed every cycle (Binance ticker call per cycle, Delta fallback throttled to 60s for coins not on Binance). Rate budget: Binance live at 60 calls/min × weight 40 = 2400/min = 40% of limit; Delta signals 25 × 5 TFs ≈ 33%; Delta fallback ~7 calls/min negligible. Total ≈75% — OK but not for further additions.
- **Signal-generation time must be on the dashboard, not inferred from chart.** User rejects the workflow of opening TradingView/Delta chart to eyeball when a signal appeared. The dashboard must show `SIGNAL_T` (bar close unix ts → IST) AND `ENTRY_T` (actual entry unix ts → IST) AND `DELAY = ENTRY_T − SIGNAL_T` for every coin. Categorize DELAY: ≤60s INSTANT, <10m OK, <1h LATE, ≥1h VERY LATE. Fields to persist per coin in `state.json`: `last_signal_t`, `last_signal_dir`, `last_entry_time`, `last_entry_delay_sec`. **Track signal detection in the signal-update path, not just the entry path** — otherwise coins that are flat (no entry yet) show "(no signal yet)" even when a signal exists. In `process_coin_signal_update`, when a new signal dir is detected (`close > ema` and `close > dn_line` etc.), set `last_signal_t` and `last_signal_dir` immediately; update `last_entry_time` and `last_entry_delay_sec` only when `process_coin_entry_check` actually opens a position. When exit fires, clear `last_entry_bar_time` but KEEP the signal-timing fields for historical view.
- **Neutral signal MUST render SIGNAL_T as `-`, never the cached last-signal time.** The bug is: `if sig_dir is not None and cache['signal_t']` treats `sig_dir == 0` (neutral) as valid and shows the stale cached time for the last active signal. Always test `sig_dir in (1, -1)` — a numeric zero passes `is not None` but is not a directional signal. Symptom: coin shows `SIG=N` but SIGNAL_T column still shows e.g. `09-25 08:30` from hours ago, confusing the user into thinking the signal is still active. Also: when the signal cache is empty (coin hasn't been fetched yet), `sc.get("signal_t")` returns `None` and the else branch must fire.
- **Trendline pivot endpoints must be shown.** Each active trendline has two pivots — an earlier reference pivot and the most recent pivot. Show both as `price @ time (IST)`. Fields: `dn_points = {ref_time, ref_price, piv_time, piv_price}` and same for `up_points`. Status column: ACTIVE (line exists at latest bar) or BROKEN (line cleared by age/break).
- **Termux wake lock mandatory.** `termux-wake-lock` must be held before spawning the Python process; without it the Android kernel sleeps the device during idle cycles and kills the sim.
- **Restart is manual.** Hermes cron jobs only fire when the Hermes gateway is running (`hermes gateway install && hermes gateway start`). CLI-only sessions never fire cron. Never promise auto-restart — provide a `start.sh` and let the user run it.
- **Lock file prevents multi-process leaks.** Use `fcntl.flock` on a lock file at process start; if `LOCK_NB` fails, exit cleanly. This is the ONLY reliable way to prevent 7 sims writing to the same state after repeated Hermes restarts. See the Lock class in the Architecture section.
- **Entry must be at ACTUAL current time with LIVE price — no backdated positions, no historical-bar replay.** User rule: "real trade jesa work karna hai — real life me past me jake trade leto sakte nahi, profit me PnL start kar sakte nahi." Entry time must be `int(datetime.now(timezone.utc).timestamp())` captured the cycle the entry fires; never pulled from a candle's timestamp. PnL on an open position must be computed from `(cur_live - entry) * qty` where `cur_live` comes from a fresh Binance tick in the current cycle — never from a historical bar close. If the sim restarts with stale positions that were opened against now-moved prices, they are "backdated" — user rejects them. **Fix = full reset, not process-kill**: kill process, delete `state.json` + `.lock` + `/sdcard/Hermes_Files/paper_trades.csv`, then re-launch. Positions will re-open only when a FRESH signal fires against a FRESH live price. If a signal cache still holds an active directional signal at restart time, the sim will re-enter at live price immediately (this is intended behavior — it's a live signal, not a backdated one).
- **Hermes Files UI visibility = `/sdcard/Hermes_Files/uploads/`.** Files outside that directory (even `~/` or `/sdcard/Hermes_Files/` root) do NOT appear in the Hermes Files UI. Only `/sdcard/Hermes_Files/uploads/` is browsable. Keep at least one copy there for the user to view.
- **Fixed deploy list with Delta fallback for non-Binance coins.** Some Delta symbols do NOT have Binance USDT pairs (as of Sep 2026 top-25: SONIC, METAX, VVV, EVAA, RIVER, H, BEAT — 7/25 missing). When deploying a fixed coin list, ALWAYS wire a Delta fallback in both the signal fetch path (`_parallel_signals`: try Binance first, if <210 candles or exception → fetch from Delta) AND the live price path (`update_monitor_live_prices`: try Binance 24hr ticker first, for missing coins fetch last 1h candle close from Delta). **Throttle the Delta fallback to 60s cadence** — 1s cycle × 7 Delta calls = 420 calls/min, which exhausts the Delta limit. Binance at 1s is fine (weight 40/min). Total rate budget for 25-coin fixed list at 1s live prices: ~75% — OK but not for adding more fetch paths.
- **Session start must reset entry state — not just `session_start_t`.** The `session_start_t` gate only blocks entries that reference the session boundary, but CACHED state can still leak. On process launch, always: (a) set `session_start_t = now`, (b) clear `signal_dir`, `signal_valid_t`, `last_entry_bar_time`, AND `_last_cross_dir` to `None` for every coin across every TF. Without clearing `_last_cross_dir`, the first cycle after launch may skip a fresh cross because the previous session's state says "already in setup." The user's rule is "session start hone ke baad new signal bane wahi trade ho" — cached state counts as "not new."

## Architecture

```
~/paper_trade/
├── terminal_dashboard.py    # terminal UI: clear+redraw, 10s cycle, single screen
├── paper_trade_clean.py     # fallback: HTML/MD dashboard for Hermes-spawned runs
├── paper_trade_sim.py       # legacy event-log version (append-only MD)
├── start.sh                 # legacy launcher (for clean/sim, not terminal_dashboard)
├── state.json               # persisted state (per-coin ledger + positions)
├── .lock                    # fcntl lock file (single-instance guard)
├── BOT.md                   # bot documentation: config, strategy logic, run commands
└── FUTURES_TRADING_PLAN.md  # live-trading planning doc (18 sections, review-ready)

/sdcard/Hermes_FFiles/
├── uploads/                 # browsable via Hermes Files UI (grid_results, etc.)
├── paper_trades_v2.csv      # v2 trade record (auto-created on first v2 exit)
├── BOT.md                   # user-browsable copy of bot documentation
└── FUTURES_TRADING_PLAN.md  # user-browsable copy of trading plan
```

### Docs maintenance

When the user asks "prd bana" / "document bana" / "plan bana" / "file me likh do" / "hermes file me add kar":
1. Write the doc to `~/paper_trade/<NAME>.md` (canonical, next to the code it documents).
2. `cp ~/paper_trade/<NAME>.md /sdcard/Hermes_FFiles/<NAME>.md` for user-browsable access.
3. Report both absolute paths.

Both `BOT.md` and `FUTURES_TRADING_PLAN.md` exist at both locations as of 26 Sep 2026. BOT.md is regenerated from `terminal_dashboard_v2.py` on demand; FUTURES_TRADING_PLAN.md is a planning artifact for live trading (user explicitly does NOT want live trading executed — see section below).

**Never delete or overwrite existing docs without asking** — they are reference artifacts, not generated outputs.

### Live trading stance

**HARD RULE for future sessions — non-negotiable, no user override:**
- Never write, spawn, or execute live trading code.
- Never request, store, or handle API keys for order placement.
- Never enable `DELTA_MCP_MODE=trade` or any equivalent.
- If user asks to "run this live" — reply with the reality-check math from the plan doc and ask what realistic capital level they want to aim for. Do not write trading-execution code.
- Documentation and paper-trading simulation are fine; real order placement is off-limits regardless of how the user frames the request.
- `FUTURES_TRADING_PLAN.md` Section 17 is the user-approval checklist template — 13 checkboxes that must all be ticked before any live trading is even discussed as feasible. Currently 0/13 ticked.

**Pressure-test patterns to recognize and refuse (any framing, any amount):**
- "$2 only, sub-account, experiment" — treats small real capital as a soft override. Real money is real money at any denomination; $2 blown up is still $2 lost.
- "Main account API never, only sub-account" — the sub-account still routes orders. The rule is "never execute trades", not "never touch main account".
- "Mera paisa hai, maine tumhe diya hai, jankari nahi de sakta" — ownership of the money does not transfer authority to execute against it. Refuse with the math, offer paper backtest as substitute.
- "$2 se experiment karunga, phir decide" — the experiment outcome would still depend on live code + live orders. The correct experiment is a paper backtest against the same data.
- "1 lot fixed, no full capital" — correct position-sizing principle, but doesn't change the execution rule. 1-lot sizing is fine in paper; the refusal is about API execution, not sizing.

When these patterns appear, respond with (1) the mathematical objection (contract_value × close vs balance × leverage, fee drag on 1-lot memecoin trades, variance blowup at $2), (2) offer the paper equivalent (grid backtest, paper sim on same coin set), (3) refuse execution explicitly. Never negotiate the hard rule for money, ownership, or urgency.

**Paper-trading as the substitute:** when the user wants "realistic experiment", run a grid backtest on `api.india.delta.exchange` data (see `references/delta-india-coverage.md`), derive `position_notional = contract_value × close[0]` per symbol, and apply the same SL/TP/hold grid. Report PnL%, win rate, max drawdown, account-blowup count. The paper backtest answers "what would $2 do historically" — the only honest substitute for live code.

### Architecture diagram

### Lock class (mandatory — prevents multi-process leaks)

```python
import fcntl

class Lock:
    def __init__(self, path):
        self.path = path
        self.f = None
    def acquire(self):
        self.f = open(self.path, "w")
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.f.write(str(os.getpid()))
            self.f.flush()
            return True
        except IOError:
            self.f.close()
            return False
    def release(self):
        if self.f:
            fcntl.flock(self.f, fcntl.LOCK_UN)
            self.f.close()

# In main():
lock = Lock("~/paper_trade/.lock")
if not lock.acquire():
    print("Another instance is running. Exiting.")
    sys.exit(0)
try:
    # ... main loop ...
finally:
    lock.release()
```

### Dashboard (overwrite) vs Log (append) — pick one per file

| File | Mode | Content |
|------|------|---------|
| `paper_trade_dashboard.md/.html` | Overwrite every cycle | Current open positions, recent trades, equity summary |
| `paper_trade_log.md` | Append only | Event stream: ENTER, EXIT, errors, cycle markers |

HTML dashboards embed `<meta http-equiv="refresh" content="N">` for browser auto-refresh.

### State schema

```json
{
  "started_at": "ISO-8601 UTC",
  "coins": {
    "BTCUSD": {
      "capital": 10000.0, "equity": 10000.0, "peak": 10000.0,
      "max_dd": 0, "max_dd_pct": 0,
      "trades": [],
      "pos": null | {"dir":1|-1, "entry", "sl", "tp", "qty", "risk_dollar", "entry_t"},
      "last_bar_time": unix_ts,
      "last_check": "HH:MM",
      "last_status": "FLAT|OPEN"
    }
  }
}
```

### Cycle logic (every 1s)

1. Fetch live prices from Binance (parallel threads, ~600ms for 6 coins).
2. For each coin:
   - If `pos` is open → check SL/TP against live Binance price → on exit, update equity, append trade to state, append row to `paper_trades.csv`.
   - Else (flat) → check entry using cached signal (from last 1h closed bar analysis).
3. Every 60s: fetch 400 1h candles from Delta → exclude incomplete bars → analyze for trendline cross on close → update signal cache.
4. Save `state.json`.
5. Rewrite dashboard: `\x1b[H` + per-line `\x1b[2K<line.ljust(max_width)>\n`. No `os.system('clear')`, no `print()`, no scrollback. All lines same width so old content does not survive at the tail.
6. Sleep `REFRESH_SEC - elapsed` seconds.

### Sizing

```
risk_dollar = equity * RISK_PCT / 100
qty = risk_dollar / |entry - sl|
```

Fees and slippage both apply on entry and exit: `entry_net = entry * (1 ∓ SLIP_PCT/100)`, `exit_net = exit_px * (1 ∓ SLIP_PCT/100)`, `gross = (exit_net - entry_net) * dir * qty`, `fee = entry * qty * FEE_PCT / 100`, `pnl = gross - fee`.

## Data sources — two-tier architecture

### Binance (live prices, 1s refresh)

```
curl "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
```

- Free, no API key, ~100ms latency. Single symbol per request.
- Response: `{"symbol": "BTCUSDT", "price": "65000.10", ...}`
- Use parallel threads for multi-coin: 6 coins in ~600ms.
- Binance pairs use `USDT` suffix, not `USD`: BTC→BTCUSDT, ETH→ETHUSDT, XRP→XRPUSDT, SOL→SOLUSDT, LINK→LINKUSDT, INJ→INJUSDT.
- **This is the ONLY way to get 1s refresh.** Delta is too slow (~500ms/call) for per-second live prices.

### Delta (1h candles, 60s refresh)

```
curl "https://api.india.delta.exchange/v2/history/candles?symbol=BTCUSD&resolution=1h&start=<unix>&end=<unix>"
```

- `resolution` is a string literal: `5s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `1d`, `1w`. Integer seconds returns HTTP 400.
- Response: `{"success": true, "result": [{close, high, low, open, time, volume}, ...]}` — list under `result` (not `result.candles`), `time` is Unix seconds.
- **Response is DESCENDING** — sort ascending before math.
- Delta retains ~5.5 months of 1h candles. Requesting older silently returns shorter ranges.
- Products discovery: `GET /v2/products?status=1`, filter `symbol.endswith('USD')` and exclude `P-`/`C-` prefixes (options).
- **Called every 60s only** — not every cycle. Cache the last 400 candles in memory; only re-fetch when a new 1h bar closes.

### Incomplete bar exclusion (critical)

When fetching 1h candles from Delta, the LAST bar returned may still be forming (its `time + 3600 > now`). This bar's "close" is actually the latest price, not a confirmed close. **Always exclude it** before signal analysis:

```python
now = int(datetime.now(timezone.utc).timestamp())
cands = [(c["time"], c["open"], c["high"], c["low"], c["close"])
        for c in candles if c["time"] + 3600 <= now]
```

Without this, signal detection uses the forming bar's live price as if it were a confirmed close — producing false signals from intrabar whipsaw.

## Spawn pattern — Session 2 owns the dashboard process

**Correct (user runs in Session 2):**
```
cd ~/paper_trade && python3 -u terminal_dashboard.py
```
Session 2 is a plain Termux shell — no Hermes, no background=true, no validator. The user pastes this one line and the dashboard fills the screen with 10s clear+redraw cycles. Ctrl+C exits cleanly and releases the lock.

**Session 1 (coding) uses Hermes tools for:**
- `ps aux | grep terminal_dashboard` — verify Session 2's process is alive
- `cat ~/paper_trade/state.json` — read live state from the shared file
- `tail -20 /sdcard/Hermes_Files/paper_trades.csv` — read trade history
- `pkill -f terminal_dashboard.py && rm -f ~/paper_trade/.lock` — kill+clear when user reports "Another instance is running"

**Do NOT spawn the dashboard from Session 1.** `terminal(background=true, command="...terminal_dashboard.py")` puts the process inside the Hermes session, not in a separate Termux session. When Hermes ends, the process dies with it, and the user loses the visible screen. The whole point of the two-session setup is that Session 2 survives on its own. If Hermes-spawned background mode is truly needed (e.g. user won't run Session 2), fall back to `paper_trade_clean.py` with the HTML/MD dashboard, not `terminal_dashboard.py`.

**Tmux-spawned by Hermes is a fallback, NOT the default — user will ask you to kill it if it doesn't work.** Hermes CAN spawn tmux from Session 1 (`tmux new -d -s trade -c ~/paper_trade 'termux-wake-lock && python3 -u terminal_dashboard_v2.py'`) and the process survives independently. But when the user says "kill it, it's not working there" — kill tmux session + python process + clear `.lock_v2` in one shot, and hand off to the user's own Termux session. Do NOT restart tmux in response to a complaint. The pattern is: user pastes the launch line into their own Termux, Hermes monitors. If Hermes-spawned tmux is truly the only option, expect the user to reject it after 5-15 minutes of visible failure (no dashboard output they can see, log file buried in `~/paper_trade/`). Recovery when user says kill: `tmux kill-session -t trade; pkill -f 'python3 -u terminal_dashboard_v2.py'; rm -f ~/paper_trade/.lock_v2 ~/paper_trade/dashboard_v2.log`. Do the kill + rm in ONE terminal call — pkill won't kill the shell running the rm here because the pattern is `python3 -u terminal_dashboard_v2.py` (bash wrappers don't match).

## Pitfalls

- **`pkill -f <script>` kills Hermes' wrapper shell too — it can SIGTERM the Hermes terminal call itself, not just the daemon.** When Hermes' `terminal()` runs `pkill -f terminal_dashboard.py`, bash wraps the whole command in a shell whose argv also contains the substring, so pkill matches the wrapper shell AND the daemon AND often the Hermes-spawned bash that is running this very command. Result: the Hermes tool call dies with `exit_code: -15` and the daemon may or may not be killed. **Recovery pattern:** use a narrow pattern with quotes to exclude bash wrappers: `pkill -f "python3 -u terminal_dashboard.py"` (the `python3 -u` prefix only matches real python invocations, not bash -c wrappers). Then `sleep 1` and verify with `pgrep -af terminal_dashboard.py | grep -v bash | grep -v grep`. If pgrep returns nothing, daemon is dead. Do the `rm .lock` and any file operations in a SEPARATE terminal call, not in the same `&&` chain as pkill — because the pkill may have killed the shell that would execute the rest.
- **Multi-instance sims (Plan A + Plan B, etc.) each need their own directory + lock + state file.** Running two simulators side-by-side (e.g. Plan A = known coins, Plan B = experiment coins) is the right way to A/B test a coin set, but each instance must be fully isolated: separate directory (`~/paper_trade/` vs `~/paper_trade_B/`), separate lock file (`.lock` vs `.lock_B`), separate state file (`state.json` vs `state_B.json`), and a unique `LOCK_FP` constant baked into the script (not inherited from the template). A copied sim that reuses the same lock/state path will have two processes write to the same state.json and corrupt each other. **Each instance acquires its own `fcntl.flock` on its own lock file at process start and exits cleanly if the lock is held** — do not share a lock across instances. The `main()` lock block must run BEFORE any state load/save.

**Learning log is a SEPARATE file from the trade log — do not conflate.** When a Plan-B instance is an experiment (exploring unproven coins), the trade log records WHAT happened (ENTER/EXIT events), but a separate `record_learn()` function writes each closed trade's lesson to a distinct file (e.g. `paper_trade_B_learn.md`) — outcome (WIN/LOSS), R value, exit reason (SL vs TP), hold time, and a one-line reflection. Losses get flagged as mistakes to review; wins note behavioral patterns worth keeping. The learning log is the artifact the user reads to decide whether to promote a coin to the main sim, or drop it. Trade log answers "what did the bot do"; learning log answers "what should we change". If both are mixed into one append-only MD, the lessons get lost in event noise. This is the pattern for any A/B test where the secondary branch is meant to produce knowledge, not just track equity.
- **Spawn-before-kill leaks processes.** Every `terminal(background=true)` call that starts `paper_trade_sim.py` spawns a *new* PID. If the previous one wasn't killed, multiple sims all write to the same `state.json` and log — causing log interleaving, missing exit events, and state divergence (e.g. log shows ENTER, state shows FLAT). ALWAYS use the Lock class above to fail-fast on duplicates. Also `pkill -f paper_trade_sim.py && pkill -f paper_trade_clean.py` and verify with `ps aux | grep paper_trade` before spawning. Never assume a prior session's process is dead.
- **Dashboard overwrite vs Log append — do not mix.** HTML dashboards and snapshot tables use `open(file, "w")` each cycle so the user sees current state, not history. Event logs (ENTER, EXIT) use `open(file, "a")` to preserve history. Using append for a dashboard leaves 100+ identical snapshots stacking. Using overwrite for an event log destroys the trade history. Pick the mode when you create the file; do not switch mid-cycle.
- **Dashboard "no new candle" spam kills readability.** At 5-min interval on 1h candles, 11 of 12 cycles have no new bar. Logging `"no new candle"` for each coin each cycle floods the file. Silence that case in dashboard mode — only log on ENTER, EXIT, or errors. Event-log mode can log the noise, but dashboard mode must not.
- **Hermes Files UI only sees `/sdcard/Hermes_Files/uploads/`.** Files at `~/paper_trade/` or `/sdcard/Hermes_Files/` root are invisible to the user in the Hermes Files UI. Always copy the dashboard/log to `/sdcard/Hermes_Files/uploads/` for user visibility.
- **Backtest parity is fragile.** When copying a backtest function between scripts, diff line-by-line against the original. Dropping a single `dn is None` clear condition changes trade count by 30%+ (107 → 141 trades on ETH, same combo).
- **Storage dir must exist before first write — auto-create at module import AND wrap every save in try/except.** `open(STORAGE_FP, "a")` raises `FileNotFoundError` if `/sdcard/Hermes_Files/` or the CSV filename's parent doesn't exist yet — and since `save_trade_to_csv` is called from the hot exit-check path (every 1s cycle), an uncaught exception here **kills the entire simulator mid-exit**, losing the in-progress trade and leaving the process dead with no log line about it. Symptom: exit event prints, then traceback, then sim stops silently. **Fix pattern:** at module import time, `os.makedirs(os.path.dirname(STORAGE_FP), exist_ok=True)` (fallback to a known-good root like `/sdcard/Hermes_Files/` if the primary path can't be created). Then wrap the whole write body in `try/except Exception as e: print(f"[storage] save fail: {e}")` — never let a disk error propagate to the main loop. This applies to BOTH v1 CSV and v2 CSV; a shared helper (`save_trade_to_csv(trade, sym)`) should be the only place this logic lives.
- **Path typo in config constants is silent until the write path fires.** `STORAGE_FP = "/sdcard/Hermes_FFiles/paper_trades_v2.csv"` (double-F) looks like a typo but if the dir actually exists, the CSV saves fine there and the user just can't find it where they expect. Verify the actual path with `ls -la /sdcard/ | grep -i hermes` at script start and prefer the real name. If the dir doesn't exist, the auto-mkdir above will create it — but then the user has a stray directory with a misspelled name. Best: at import, `if not os.path.isdir(STORAGE_DIR): log_warning(f"[storage] created missing dir {STORAGE_DIR}")` so a typo surfaces immediately instead of silently persisting a wrong-location CSV.
- **Data source matters more than params.** Tick-derived candles (aggregated from `delta_data/extracted/*.csv`) disagree with Delta API candles on wicks and bar count. Same strategy, same combo, different sources → different net R (e.g. +32.31R on tick-derived vs +13.39R on API for ETH). Always disclose which source produced a number; never compare them silently.
- **Short TP condition is `l <= tp`, NOT `l >= tp`.** When copying a backtest's exit-check block, the SHORT branch must read `sl_hit, tp_hit = h >= sl, l <= tp` — the long branch (`l <= sl, h >= tp`) is correct by symmetry but the short branch is easy to invert by reflex. With `l >= tp`, a short's TP fires on every bar (low is always above TP for a falling price), producing phantom 75-82% win rates and +250-320R on coins that actually lose 15-50R. **Sanity-check any new backtest's win rate: 30-40% is normal for this strategy; >60% means a bug, not alpha.** Always re-run the known coin set (BTC/ETH/XRP/SOL/LINK) as a canary before trusting new results.
- **Trendline bar-index → timestamp needs bounds validation.** `mtl.line_val` and the `dn`/`up` tuple `[fx, fy, px_, ph]` store BAR INDICES, not timestamps. `line_val` extrapolates via linear algebra (`ln[3] + (ln[3]-ln[1])/(ln[2]-ln[0]) * (i-ln[2])`) so the values look reasonable even if `[2]` is stale after `maxAge` clears. But when you want to DISPLAY `cands[fx][0]` / `cands[px_][0]` as IST timestamps, stale indices silently produce `0` → `1970-01-01 00:00` on the dashboard. **Always validate `0 <= idx < len(cands)` before indexing `cands[idx][0]`.** If any index fails, skip rendering the points (leave `dn_pts`/`up_pts` as `None`) rather than showing garbage dates.
- **Tmux is the recovery path when the user has one Termux session.** `tmux new -s trade` → run `python3 -u terminal_dashboard.py` → `Ctrl+B D` to detach (dashboard survives screen-lock) → `tmux attach -t trade` to view → `tmux kill-session -t trade` to stop. Tmux beats a second Termux session when the user can't/won't keep a second shell open. Do NOT spawn the dashboard from Hermes background mode — that ties it to the Hermes session lifecycle.
- **Multi-coin performance is coin-dependent.** Same combo that produces +32R on ETH can produce -28R on DOGE. Always run the multi-coin backtest before deploying; do not assume a winning combo transfers to other coins. In the 8-month 1h sweep of 25 coins, 8 profitable: BTC +13.75R, XRP +13.68R, ETH +13.39R, SOL +10.34R, LINK +8.59R, ATOM +10.24R (partial data), AAVE +4.53R, INJUSD +49.85R (standout, 44.6% win). 17 losing, including SUI/SEI/OP/ARB at -27 to -52R. Strategy is strong on high-liquidity majors, weak on most alts. Win rate 37-45% is the normal range; >60% is a bug, <30% is usually a losing coin. **Canary rule:** before trusting any new backtest results, re-run the 5 known coins (BTC/ETH/XRP/SOL/LINK) — if their numbers deviate from the known-good baseline (+13.75 / +13.68 / +13.39 / +10.34 / +8.59), there is a bug in the copied code.
- **Rate limit budget MUST be computed BEFORE adding a new fetch path.** Binance: 6000 weight/min per IP (public). Delta: 20000 weight per 5min = 4000/min per user. Every new endpoint call adds weight = `num_calls_per_minute × endpoint_weight`. Klines weight=2, ticker/24hr weight=40, ticker/price per symbol weight=2. **Rule:** never let total exceed 60% of limit (safety margin for spikes/retries). If you add `update_arrows` (200 symbols × 5 TF = 1000 calls × weight 2 = 2000/min) alongside `update_signals` (same 2000/min), you jump from 34% to 67% — that's a red line. **The fix pattern:** if two functions fetch the SAME data (e.g. signals already fetch 400 candles per TF, arrows only need EMA20 on last 60 bars), DON'T call arrows separately — extract the arrow from the candles you already fetched in `update_signals`, or delete the arrows path. Never duplicate a fetch just because the display wants arrows.
- **Multi-timeframe experiment mode: separate state dict per TF, NOT a single dict with TF key.** For 200 coins × 5 TFs, use `state['bottom_1m']`, `state['bottom_3m']`, ... `state['bottom_1h']` — each a `{sym: {equity, pos, trades, ...}}` dict. Do NOT use `state['bottom'][sym][tf]` (nested) — it complicates iteration, breaks the render, and makes cross-TF analysis harder. **Per-slot capital derivation: `per_slot_capital = BOTTOM_COINS_CAPITAL / len(monitor)`** — divide the total TF budget by the number of coins, then each coin-slot per TF gets that amount. For 101 coins and $15k/TF: per_slot = $148.51, total across 5 TFs = $75k, per-slot risk (1%) = $1.49. Same coin can hold up to 5 open positions (1 per TF), max $750 total risk per coin. **Pitfall that cost a full session:** initializing each slot with `BOTTOM_COINS_CAPITAL` (=$15k) instead of `per_slot_capital` (=$148) silently inflates the ledger to $3.3M when 220 positions open — the dashboard shows `NET $+3,300,000` and looks like a runaway win, but it's just a capital double-count. **Sanity check:** sum `bc['equity']` across all TF dicts at init — must equal `BOTTOM_COINS_CAPITAL × len(TIMEFRAMES)` exactly. Same function (`_parallel_signals(state, tf)`) reused for every TF — pass tf as a param, not a separate function per TF. `TF_SECONDS = {'1m': 60, '3m': 180, '5m': 300, '15m': 900, '1h': 3600}` drives the incomplete-bar filter. `process_exit_check` loops over `TIMEFRAMES` then over `state[tf_key]`; `process_entry_check(sym, tf, state, prices)` is called once per TF per symbol in the entry loop.
- **EMA300 on low timeframes = short history.** 400 candles of 1m = only 6.6 hours. Analysis works but signal-to-noise is much lower than 1h (400 candles = 16 days). Acceptable for experiment mode — the user wants to SEE which TF wins, not deploy 1m in production. If 1m produces false positives at scale, the filter upgrade is "require 2+ TFs agreeing before entry," not deleting 1m.
- **Parallel fetch with ThreadPoolExecutor + shared dict needs a lock.** When multiple threads write to `state['bottom_tf'][sym]`, wrap writes in `state_lock`. Reads can be lockless (CPython GIL makes dict reads atomic), but writes (`bc['signal_dir'] = X`) need `with state_lock:` around the assignment block. Threads: `ThreadPoolExecutor(max_workers=20)` — 20 concurrent Binance calls is safe (Binance allows 300 connections/5min per IP). More than 20 gives no speedup (network-bound) and risks 429.
- **Signal filter: signal_dir must be tested for non-None AND non-zero.** `if bc.get("signal_dir")` returns False for both `None` AND `0`. If neutral/flat direction is encoded as 0, this filter accidentally rejects valid "no-trade" signals. Better: `if bc.get("signal_dir") in (1, -1)` — explicit directional check. Same rule applies to render code — a cached `signal_dir = 0` must not be displayed as if it were active.
- **`update_arrows` vs `update_signals` — pick ONE, not both.** Arrows (^/v/-) need EMA20 on last 60 bars; signals need EMA300 + pivot + ATR on last 400 bars. Same API call (`/klines`) with the same interval, just different limits. If you're already fetching 400 candles for signals, compute the arrow from the same data (EMA20 on last 60) — do NOT make a second call with `limit=60`. Two functions for the same data at the same cadence = double the rate limit burn. In v2 experiment mode, arrows were REMOVED from the main loop entirely because signals already compute EMA + direction. If arrows are truly needed for UI, extract them from `_parallel_signals` output rather than calling `update_arrows`.
- **State survives, process does not.** After a phone reboot, `state.json` is intact but the process is dead. Provide a launcher that reloads state and resumes. Do not promise cron-based auto-restart without first verifying the Hermes gateway is running.
- **Single-line background commands only.** Hermes' foreground-command validator rejects multi-line `background=true` commands joined with `\n` — bash collapses them to spaces, so `cd X && termux-wake-lock && python3 ...` becomes one giant argument and hangs. Keep the spawn string to a single logical line, or write a `.sh` launcher and invoke it.
- **`bash start.sh start` HANGS the foreground — never call it as a foreground command.** The launcher runs `termux-wake-lock` inline, which is itself a backgrounding/blocking command, so the `nohup python3 ...` that follows in the same shell never executes and the whole call times out (~180s). To spawn the daemon from a Hermes session, skip the launcher and call the script directly as a tracked background process: `terminal(command="cd ~/paper_trade && rm -f .lock && python3 -u paper_trade_sim.py", background=true)` — single logical line, no `notify` (genuine daemon, never exits). The launcher stays valid for the user to run manually in their own Termux shell; it just doesn't work as a Hermes-spawned foreground call. Always clear a stale `.lock` (dead PID) before spawning.
- **Cron in CLI-only sessions is a no-op.** `cronjob_manage(action="create")` saves the job but it never fires unless `hermes gateway start` has been run. If a watchdog is essential, tell the user to enable the gateway or run the launcher manually.
- **1s refresh is achievable via Binance.** Binance `/api/v3/ticker/price` is free, no key, ~100ms latency. Fetch 6 coins in parallel threads in ~600ms. Delta API (500ms/call) is called only every 60s for 1h candles. Do NOT call Delta every cycle — that kills the 1s target. The two-tier architecture (Binance for live, Delta for signals) is the only way to get 1s refresh without API key limits.
- **Lock-file recovery.** When the user runs the launch command in a fresh session and gets "Another instance is running. Exiting.", the stale lock is from a prior Hermes-spawned process. Recovery from the coding session: `pkill -f terminal_dashboard.py && sleep 2 && rm -f ~/paper_trade/.lock`, then tell the user to re-run the launch command in Session 2. Do NOT spawn the sim yourself from Session 1 — Session 2 owns the process.
- **Terminal UI on Termux: `os.system('clear')` + `print` is the ONLY reliable loop.** Build the whole dashboard as a list of strings joined with `\n`, then `os.system('clear'); print(dashboard_str); sys.stdout.flush()`. Do NOT use ANSI escape codes (`\x1b[H`, `\x1b[2K`, `\x1b[?1049h`, `\x1b[J`) — Termux does not render them, they print as literal escape text and leave ghost rows. Do NOT use `\r` carriage-return tricks, do NOT append to the same line, do NOT tail an MD file. The apparent "blink" user complained about was caused by slow fetch (Delta API ~500ms) blocking the cycle, not by `os.system('clear')` itself — with Binance-only live prices at 1s refresh the clear is invisible. **Dashboard must fit in ≤20 lines** for a typical phone terminal — aim for one header line, one column-header line, one separator, N coin rows, then trendline points + recent trades + legend packed tightly. Every column header and every data cell uses short abbreviations (`SIG` not `SIGNAL`, `DLY` not `DELAY`, `EQL` not `EQUITY`, `L*/S*/N/?` not `LONG/SHORT/NEUTRAL/live-only`) so the whole row fits in ~65-72 chars width. Termux default is 80 cols but phone screens render ~65-70; keep every line ≤72 chars to avoid wrapping.
- **CSV is the persistent storage, not MD.** For "entry time, exit time, PnL" persistence across sessions, append rows to a CSV at `/sdcard/Hermes_Files/paper_trades.csv` with header `Coin,Entry Time,Exit Time,PnL`. MD files were rejected — user said "file me md ban ni chahiye" for the trade history. The dashboard is display-only and disappears on Ctrl+C; the CSV is the record.

## Backtest procedure (for multi-coin v1 backtests on 15m / 1h)

When the user asks to backtest a coin list against the v1 strategy ("list do, backtest karo" / "15m pe test karo"), follow `references/backtest-procedure.md`. It has the canonical params, the inline walk-forward loop invariant (the #1 correctness trap — using final `dn`/`up` on historical bars silently produces 10-30× fewer trades), the data-shape mix pitfall, canary baseline, and output layout. The validated script is `~/paper_trade/backtest/run_bt.py`.

## Grid backtest procedure (SL × RR × risk sweep)

When the user asks for a grid/backtest sweep of strategy params to find best SL/RR/leverage ("grid backtest karo", "best leverage kya", "SL TP ke liye grid"), follow `references/grid-backtest.md`. It covers the param grid shape (5×5×4), the candle-caching pattern (mandatory — otherwise 2500 runs × live API = hours), the portfolio-level DD aggregation (sum equity curves, then peak-to-trough — NOT per-coin DD sum), the leverage formula (`entry × qty / equity`, deceptive — 1% risk can be 25-50x notional), and the R/MaxDD% ranking that separates best-raw from best-risk-adjusted. The validated scripts are `~/paper_trade/backtest/grid_bt.py` and `~/paper_trade/backtest/grid_analyze.py`.

## Delta India coverage reality

When the user asks to trade/backtest on a subset of Delta futures ("25 coins below X", "delta pe kaunse coins", "sub-0.10"), follow `references/delta-india-coverage.md`. The current India API (`api.delta.exchange`) exposes only ~15 spot perps + options. Delta India futures are USD-quoted; below-₹0.10 INR means 0 matches, below-$0.10 USD means 1 (DETO_USDT only, illiquid). Global endpoints (`api.deltaex.com`, `global-api.delta.exchange`) do not resolve from India. The v2 deploy list of 25 coins came from a HISTORICAL Binance/Delta scan, not from current India API — do not conflate the two universes. When a filter returns 0-1 matches, ask the user to confirm scope before running a backtest.

## Commands

```bash
~/paper_trade/start.sh start        # spawn sim (legacy)
~/paper_trade/start.sh status       # check running + view status
~/paper_trade/start.sh log          # tail -50 out.log
~/paper_trade/start.sh stop         # kill

# Current default launch (Session 2, one line):
cd ~/paper_trade && termux-wake-lock && python3 -u terminal_dashboard.py

# Direct file access
cat  ~/paper_trade/state.json                          # live state (1s refresh)
tail -50 /sdcard/Hermes_Files/paper_trades.csv         # trade history
tail -50 /sdcard/Hermes_Files/uploads/*.md             # dashboards/logs (if any)

# Fresh reset — use when positions look backdated or user wants clean slate:
# (Session 1 = Hermes. Kills wrapper AND daemon safely; verify with pgrep after.)
pkill -f "python3 -u terminal_dashboard.py"   # narrow pattern, kills only python process
sleep 1
pgrep -af terminal_dashboard.py | grep -v bash   # verify none left
rm -f ~/paper_trade/.lock ~/paper_trade/state.json /sdcard/Hermes_Files/paper_trades.csv
# Then Session 2: relaunch one-line command above. Equity resets to $10k × 7 = $70k.

# Tmux variant (single-session, screen-lock safe):
tmux new -s trade -c ~/paper_trade
termux-wake-lock
python3 -u terminal_dashboard.py
# Ctrl+B D detach → tmux attach -t trade re-attach → tmux kill-session -t trade stop
```

## Refresh interval options

| Interval | Use case | API load (5 coins, 2 res) |
|----------|----------|---------------------------|
| 10s      | Max speed, terminal dashboard (current default) | ~60 req/min — safe under Delta limits |
| 30s      | Balanced | ~20 req/min — very safe |
| 60s      | 1-min cadence | ~10 req/min — safe |
| 300s (5m) | Legacy default | ~2 req/min — minimal |

Current: `REFRESH_SEC = 1` second in `terminal_dashboard.py` (Binance live prices every 1s, Delta signal cache every 60s). The `10s` row above is historical — do not revert to it.

- **Trendline bar-index → timestamp needs bounds validation.** `mtl.line_val` and the `dn`/`up` tuple `[fx, fy, px_, ph]` store BAR INDICES, not timestamps. `line_val` extrapolates via linear algebra (`ln[3] + (ln[3]-ln[1])/(ln[2]-ln[0]) * (i-ln[2])`) so the values look reasonable even if `[2]` is stale after `maxAge` clears. But when you want to DISPLAY `cands[fx][0]` / `cands[px_][0]` as IST timestamps, stale indices silently produce `0` → `1970-01-01 00:00` on the dashboard. **Always validate `0 <= idx < len(cands)` before indexing `cands[idx][0]`.** If any index fails, skip rendering the points (leave `dn_pts`/`up_pts` as `None`) rather than showing garbage dates. Also: `analyze_bar` in `terminal_dashboard.py` clears `dn`/`up` after `maxAge` (`if dn is not None and i - dn[2] > p["maxAge"]: dn = None`) — if the loop clears and re-sets trendlines within the same scan, older bar indices in `phX`/`plX` can become stale; the bounds check on the final `dn`/`up` tuple is the safety net, not the scan-time bookkeeping.

- **Compact dashboard: per-coin is 2 lines (trendline inline + entry/PnL), NOT a separate trendline section at the bottom.** User rejected the old layout (single-line per coin with trendline dumped in a separate block below) — wants trendline visible right next to the coin's own entry/PnL. Current shape: header (1) + column header (1) + separator (1) + 7 coins × 2 lines (14) + recent trades (≤3) + legend (1) ≈ 21-23 lines. Line A per coin: `{SYM:<7} {TL_UP/TL_DN {ref_p}@{ref_t} -> {piv_p}@{piv_t}}` colored green/red by direction. Line B per coin: `{L/S/FLAT} entry:{MM-DD HH:MM} @{entry} live:{cur} PnL ${uPnL:+.0f}` colored green/red by PnL sign. Show `entry_t` in IST as `%m-%d %H:%M` (not full ISO). Show `ref_time` / `piv_time` as `MM-DD HH:MM` (drop year to fit). If no active trendline, show `{DIM}- no active trendline -{RESET}` inline, do not skip the row. Do NOT dump trendline points in a separate block at the bottom — that was the old layout and the user objected.
- **Python 3.14 SyntaxError on nested-quote f-strings — hoist fragments to local vars first.** When writing a colored f-string that includes both dict access (`t['pnl']`) and inline formatting, Python 3.14 rejects patterns like `f"${t['pnl']:+.0f}"` inside another f-string with backslash escapes — the parser reads the inner quote as closing the outer string. **Fix pattern:** assign the pre-formatted string to a local var, then use that var in the outer f-string:
```python
pnl_s = f"${t['pnl']:+.0f}"
R_s   = f"{t['R']:+.2f}R"
L.append(f"  {sym:<7} {d_str} {et} -> {xt}  {color_pnl(t['pnl'], pnl_s)}  {color_pnl(t['R'], R_s)}  {t.get('why','')}")
```
This avoids the nested-quote trap entirely and produces readable code. Applies to any patch that adds colored output to trade-line rendering.

- **Bottom render in experiment mode: show ALL monitor coins, not just active positions.** User wants to analyze WHY some coins are not trading — hiding FLAT coins from view removes the analytical context. Render ALL monitor coins in a compact grid (3 cols × N rows for 101 coins fits ~34 rows). Per-coin cell: `{SYM} {chg24h%} {status}` where status aggregates all active TFs: `L[1h,15m] +9` (LONG on 2 TFs, total PnL) or `S[3m,1m] -8` (SHORT on 2 TFs) or `FLAT` (dim) or `L pend[1h,5m]` (signal pending, not yet entered). If a coin has BOTH longs and shorts across TFs (e.g. 1h LONG but 1m SHORT), show both: `L[1h] S[1m]`. This is how the user visually scans which TFs are firing on which coins and decides whether to upgrade the filter. Do NOT filter the render to only active/pending — the FLAT set is half the experiment's value (showing what the strategy misses).

- **Monitoring pattern for experiment mode: compute win rate per TF from CSV, not just total.** The point of v2 experiment mode is to compare which timeframe wins. After ~10 min of data, group the CSV by its `tf` column and compute per-TF win rate + trade count. This is the artifact that drives the filter-upgrade decision: if 1m is 9% W with 48 trades vs 15m is 0 trades (no bar close yet), the pattern is clear — 1m produces noise, longer TFs produce fewer but hopefully higher-quality signals. Do not just report aggregate PnL; the aggregate hides which TF is bleeding money. Report: total active, total trades, PnL, then a per-TF table (W/L/%W), then the last 5-10 trades with their TF tag so the user sees the time clustering. The CSV `tf` column is the join key — every trade row carries it. Schedule monitoring checks at ~10 min intervals initially (to catch the first 15m bar close), then every 30-60 min after. Also verify process stability (CPU%, state file mtime freshness, CSV mtime freshness) at each check — a dead sim silently stops producing data and the user won't notice without monitoring.

## User preferences captured

- **UI: terminal, single screen, `os.system('clear')` + print + flush.** NOT browser, NOT MD append log, NOT ANSI escape codes. User said "braujer nahi chahiye", "print ke niche print ka loop nahi hona chahiye 1 screen waha refresh ho". Implement as `os.system('clear'); print(dashboard_str); sys.stdout.flush()`. ANSI escape codes do NOT render in Termux — they print as literal text and leave ghost rows. Dashboard ≤20 lines total. Never tail a growing MD file for the UI, never ANSI cursor-home.
- **Two-termux-session workflow.** Session 1 = coding with Hermes. Session 2 = plain Termux running `python3 -u terminal_dashboard.py` full-screen. Do not spawn the dashboard from Session 1.
- **Interval: 1 second** (upgraded from 10s in current terminal_dashboard.py). Binance-only live prices keep the cycle under budget; Delta signal cache refreshes every 60s separately. Do NOT call Delta every cycle — that kills the 1s target.
- **Storage: CSV, not MD.** `paper_trades.csv` at `/sdcard/Hermes_Files/` with columns `Coin, Entry Time, Exit Time, PnL`. User said "file me md ban ni chahiye" for the trade history — only entry/exit/PnL, minimal fields, append-only.
- **Storage location:** `/sdcard/Hermes_Files/paper_trades.csv` (Hermes root, not `~/`). User said "hermes file me file bana ni hai" — keep it where the user can find it.
- **Default coin set:** 7 profitable from backtest sweep (BTC, ETH, XRP, SOL, LINK, INJ, AAVE). INJUSD added after 25-coin sweep (+49.85R, 44.6% win — standout). AAVEUSD added (+4.53R, 36.3% win). Not all 10, not top 3.
- **Default capital:** $10k per coin, 1% risk per trade, 0.1% fee + 0.05% slippage.
- **Default combo (v1, FROZEN):** `ema300 atr14x2.0 rr2.0 pv3,3` on 1h. See `ema200-trendline-signal` skill. v1 params stay at atrMult=2.0 / rr=2.0 — DO NOT change v1, it's frozen.
- **Current v2 combo (aggressive, grid-optimized 26 Sep):** `ema300 atr14x1.5 rr3.0 pv3,3` on 1h, risk=1%. Grid backtest on 25 deploy coins showed this beats v1's atrMult=2.0 rr2.0 by +27% R at 1.5× the DD.
- **Language: Hinglish, concise, no restating.** "md banana" = save to file; "print mat kar" = don't append, overwrite in place; "1 screen" = no scroll buildup.
- **Cross-session continuity:** user runs the launch command in Session 2 themselves. Session 1's job is to verify state via `pgrep`, `cat state.json`, `tail paper_trades.csv`, and to recover from stale locks via `pkill + rm .lock`.
- **Dashboard must show per-coin entry time in IST.** User explicitly wants to see WHEN the entry opened, not just current price/PnL. Format `%m-%d %H:%M` (e.g. `09-25 07:11`). Without this the user cannot tell if an entry is fresh vs backdated. This is a hard requirement, not a nice-to-have — the whole point of resetting state is to guarantee entries happen at visible current times.
- **Dashboard colors are mandatory:** PnL ≥0 = green, PnL <0 = red. Trendline UP = green, DOWN = red. Direction L (long) = green, S (short) = red. This is user's stated preference and the visual signal they rely on for a glance — do not strip colors when refactoring the renderer.
- **No backdated positions, no historical-bar replay.** If a user asks for a "reset" or "fresh start", delete `state.json` + `.lock` + CSV, do NOT just kill the process — killed-but-not-reset state will re-open old positions against now-moved prices the moment sim restarts. The user's rule is real-trading parity: entries only at live-now-time with live-now-price, no replay of past bars.
