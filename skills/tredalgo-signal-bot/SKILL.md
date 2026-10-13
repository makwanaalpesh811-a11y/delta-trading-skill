---
name: tredalgo-signal-bot
description: Maintain tredalgo_signal_bot.py — Pine-style PNG chart bot.
metadata:
  hermes:
    tags: [trading, telegram, pillow, chart, tredalgo]
    category: devops
    related_skills: [paper-trade-simulator, telegram-standalone-bot]
---

# TREDALGO Signal Bot

Standalone script at `~/tredalgo_signal_bot.py` — independent of Hermes and of `paper_trade/engine.py`. Fetches Delta India 1h candles for 25 coins, runs `analyze()` (EMA300 + trendline breakout + ATR SL/TP), renders a Pine-style chart PNG via Pillow, sends to Telegram.

## When to use
- Modifying chart rendering (canvas size, layout, labels, colors, fonts).
- Deploying the bot (bg process, log location, restart after edits).
- Debugging signal logic (`analyze()`) or Telegram delivery (`send_photo`/`broadcast`).
- Regenerating historical signal charts for review.

Do NOT use for the paper-trade engine (`paper_trade/engine.py`) — that is the `paper-trade-simulator` skill. Do NOT use for the Telegram dashboard bot (`paper_trade/tredalgo_bot.py`).

## Non-negotiable: chart code rewrite discipline

When the user asks for a `draw_chart()` rewrite or a major chart refactor, write the ENTIRE file with one `write_file` call. Do NOT write it and then use `patch` to fix bugs surfaced during testing. `patch` is for surgical tweaks the user has not asked to rework; a rewrite task means clean single-shot delivery. If the user's rewrite request produced a bug, fix it by re-writing the whole file, not by patching.

## Procedure: chart rewrite

1. Read the current file end-to-end (`read_file` with full range, not paginated chunks — the pagination warning is a hint that you haven't read the whole thing).
2. Design the new `draw_chart()` with all bugs fixed upfront. Known traps to fix in one pass:
   - Format string for Y-axis price labels — see "Y-axis label format" pitfall.
   - Signal ring draw order — see "Ring draw order" pitfall.
   - Label collision avoidance — see "Label collision" pitfall.
   - Skip current-price tag when it would overlap a gridline label — otherwise the axis label is unreadable.
3. Write the entire file in ONE `write_file` call. Everything else (`analyze`, `ema_series`, `atr_series`, `line_val`, `fetch_candles`, `send_photo`, `broadcast`, `load_state`, `save_state`, `main`) must be copied character-for-character from the current file unless the user asked to change it.
4. Test with `python3 -m py_compile` first. Then run a test harness that generates fake LONG + SHORT signals for a few coins and renders PNGs.
5. Verify with vision_analyze: y-axis labels unique, entry ring visible, no overlap, last candle visible.
6. Verify function integrity — see "Verify function integrity after surgery" below.

## Canvas specs (TradingView style, 1080×1350 portrait)

Current layout (post-simple-rewrite — replaces the old Pine-style 4-box version):

- BG `(20, 22, 32)`
- `padL=50, padR=150, padT=100, padB=60`
- VISIBLE = 50 candles + 10 blank columns on the right (for trade box + right-axis tags)
- Total columns = 60; `col_w = plot_w / TOTAL_COLS`; `X(col) = padL + col_w * (col + 0.5)`
- Font sizes: title 30, tags 22, axis 20, subtitle 20
- Load real TTF fonts (DejaVuSans-Bold, Roboto-Bold) with fallback to `load_default(size=...)`; print a warning if fallback.
- **No bottom boxes, no pivot dots, no signal ring, no dashed TP/SL lines, no old/historical trendlines.** Just: bg + grid + 2 trendlines + trade box + EMA + candles + arrow + 3 right-axis tags + title/subtitle.

## Draw order (current — order matters)

1. BG + horizontal grid + right price axis labels (step from `_nice_step`, `_decimals`).
2. Vertical grid + time labels (IST, `%H:%M`, every 8 bars).
3. Trade box: signal candle x → right edge. Two alpha-45 rectangles composited back onto RGB: green `(0,220,120,45)` between ENTRY↔TP, red `(240,80,80,45)` between ENTRY↔SL. LONG: TP above entry, SL below; SHORT: opposite.
4. EMA300 (white, width 2), clipped to plot area.
5. **Two trendlines always both drawn (jo available ho):**
   - Resistance (sig['dn']): TEAL `(0,150,136)`, width 3, label color `(0,200,180)`.
   - Support (sig['up']): RED `(255,60,80)`, width 3, label color `(255,120,130)`.
   - Extend from pivot1 to `TOTAL_COLS-1` (past the signal candle into the trade zone). Clip to plot rect. The break is visible because the line continues through the signal candle while the signal candle closes on the other side of it.
   - `extend_to_right=False` option available to end the line at `VISIBLE-1` (signal candle x). Use to make the break unambiguous in a specific chart; default keeps both lines extending.
6. Arrow at signal candle: LONG = green triangle below candle high (points up); SHORT = red triangle above candle low (points down).
7. Candles (body width 60% of step, min body height 3px, green `(0,170,120)` / red `(240,80,80)`) drawn on top of everything.
8. Right-axis price tags (3): TP green `(0,170,120)`, SL red `(240,80,80)`, ENTRY yellow `(255,200,60)`. Rounded rect, 4-sig-digit labels, min 28px vertical gap enforced by shifting down.
9. Title top-left orange 30px: `{SYM} 1h  {LONG/SHORT}  {dd Mon HH:MM IST}`.
10. Subtitle grey 20px: `RR 1:2 | ATR x2 | EMA300`.

## Chart helpers

- `_nice_step(lo, hi, ticks=8)`: `raw = (hi-lo)/ticks`, snap to `1/2/2.5/5/10 × 10^floor(log10(raw))`.
- `_decimals(step)`: minimum decimals that exactly represent `step`.
- `_fmt_price(v, dec)`: `format(v, "." + str(dec) + "f")` — never use `%`-style format in an f-string.
- `_sigfmt(v)`: **exactly 4 significant digits** for labels. Formula (do not use the old `≥100/.3f` bucket rule):
  ```python
  if v == 0: return "0.0000"
  av = abs(v)
  if av >= 1:
      dec = max(0, 3 - int(math.floor(math.log10(av))))
  else:
      dec = -int(math.floor(math.log10(av))) + 3
  r = round(v * 10**dec) / 10**dec
  return format(r, "." + str(dec) + "f")
  ```
  Reference outputs (verify after any edit): 0.3339→`0.3339`, 0.334→`0.3340`, 0.01698→`0.01698`, 14.09→`14.09`, 720.5→`720.5`, 2545.3→`2545`.
- `_dashed_line(dr, p1, p2, fill, width, dash, gap)` — kept for other uses, not used by the current chart.
- `_text_bg(dr, xy, text, font, fg, bg, border, pad=6)` — kept for compatibility, not used by the current chart.
- `_clip_line(pts, bounds)`: returns list of sub-polygons inside bounds (for EMA clipping).

## Pitfalls

**Format-string trap**: `"%.{dec}f".format(v, dec)` and `"{:." + str(dec) + "f}".format(v)` both fail — the first prints the literal `%`, the second raises `ValueError: Single '}' encountered in format string`. Build the format spec as a standalone string via `format(v, "." + str(dec) + "f")` (helper `_fmt_price`) or a pre-built spec string.

**Ring draw order**: if you draw the signal ring before candles, it gets covered; if you draw it before the label box, the label's opaque bg covers it. Draw the ring AFTER all labels and set its center to the last candle's mid-body (`(c_top + c_bot) / 2`), not the entry close. Size the radius to at least 1.8× the candle body height so it clearly surrounds the candle.

**Label collision**: TP/ENTRY/SL labels near each other (small ATR, small RR) will overlap. Maintain a `placed` list of `(x, y, w, h)` and shift each label up by 28px until it stops colliding; clamp to plot top.

**Current-price tag overlap**: if `ep_y` is within 20px of a gridline label, the price tag on the right axis covers that axis label. Detect by walking the gridline y-positions and skipping the tag if any is close. The axis label is more important than the tag.

**EMA/trendline scale rule**: EMA can wander far from the price range over 50 bars and skew the y-scale. Compute `cmax`/`cmin` from `candle_highs + lows + [sl, tp, ep]` first. Then include EMA values in the scale ONLY if they fall within 50% of the candle range (`|ema - mid| <= c_range * 0.5`); values outside that window are clipped visually via `_clip_line` but do not widen the scale. Trendline values NEVER go into the y-scale — they are purely visual and clipped to the plot rect at render time.

**Trendline labels must not overlap candles**: the `Resistance` / `Support` text labels can sit right where candles are dense. Position each label at the line's start (left end), 14px above the line for Resistance, 14px below for Support. Before drawing, walk visible candle bodies and skip the label if its rect touches any candle high/low — labels are optional, don't sacrifice the price action for a label. Dark semi-transparent bg (`(20,22,32)`) behind each kept label so wicks behind it don't hurt readability.

**Signal arrows are directional markers, not price labels**: draw the LONG arrow as a green triangle BELOW the signal candle's high (apex up) so it visually points at the candle; draw the SHORT arrow as a red triangle ABOVE the signal candle's low (apex down). Never center the arrow on the entry close — it hides the candle body.

**Buffer**: `BUFF_MULT` is the trendline-cross delay multiplier. `0.25` (default) delays signal until price is 25% ATR past trendline — often the signal fires only after EMA cross, missing the actual breakout bar. `0` = raw cross (what the user's LINK reference chart shows). Choose per strategy; note it in a comment when setting.

## Verify function integrity after surgery

After any surgery on `draw_chart()`, confirm the untouched functions are byte-identical to their canonical bodies. Line-count comparison is unreliable (trailing blank lines shift the count). Use AST to extract the full function source by line range, then normalize (strip trailing whitespace per line + overall strip) and string-compare against a canonical copy:

```python
import ast
src = open(path).read()
tree = ast.parse(src)
lines = src.split('\n')
def get_body(name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return '\n'.join(lines[node.lineno-1:node.end_lineno])
def norm(s):
    return '\n'.join(l.rstrip() for l in s.strip().split('\n')).strip()
# compare norm(canonical) == norm(get_body(name))
```

Target functions to verify byte-identical after a `draw_chart()` rewrite: `analyze`, `ema_series`, `atr_series`, `line_val`, `send_photo`, `broadcast`, `main`.

## Deploy

```bash
pkill -f "python3 -u tredalgo"
sleep 2
pgrep -af tredalgo_signal_bot   # confirm dead
# then start
```

Run with `terminal(background=true)` (no `nohup`/`disown` — Hermes rejects those). Log: `~/tredalgo_signal_bot.log`. Charts dir: `~/tredalgo_signals/charts/`. State: `~/tredalgo_signals/sent_state.json`.

Token/chat live in the file's `BOTS` list. Verify token works with `GET https://api.telegram.org/bot<TOKEN>/getMe` before starting.

**Redacted-token fallback**: Hermes redacts the token in the on-disk file (shows `8077800501:***`). Any test/verification script that needs to send a Telegram message must either read the token from a separate `.env` / env var the user provides, or fall back to printing file paths to the user when the token looks like `...:***`. Never try to guess or reconstruct the token; it is not recoverable from the redacted form.

## Historical signal replay test (real signals, not fabricated)

Fake signals (flipping `dir`, inventing pivots) produce charts where the trendline break is not actually visible — the line is placed near the entry price by fiat, not because a real cross happened. Use real historical signals instead:

```python
from tredalgo_signal_bot import COINS, fetch_candles, analyze, draw_chart, EMA_LEN, line_val

def replay_signals(sym, cd, want_long=2, want_short=2):
    """Walk analyze() over growing windows and record every real cross."""
    n = len(cd)
    out = []
    for k in range(EMA_LEN + 5, n):
        sig = analyze(cd[:k + 1])
        if sig and sig['dir'] != 0:
            out.append((k, sig))
    return out

def verify_long(k, sig, cd):
    """LONG: close > dn line, close > EMA, dn line must exist."""
    cl = cd[k]['close']
    dn_v = line_val(*sig['dn'], k) if sig['dn'][0] is not None else None
    return (dn_v is not None and cl > dn_v
            and sig.get('ema') is not None and cl > sig['ema'])

def verify_short(k, sig, cd):
    """SHORT: close < up line, close < EMA, up line must exist."""
    cl = cd[k]['close']
    up_v = line_val(*sig['up'], k) if sig['up'][0] is not None else None
    return (up_v is not None and cl < up_v
            and sig.get('ema') is not None and cl < sig['ema'])
```

Pick 2 LONG + 2 SHORT from DIFFERENT coins (dedupe by symbol, take the latest `k` per coin). Render each with `draw_chart(sym, cd[:k+1], sig, path)`. Vision-verify: (1) the broken line's trend direction matches the signal — resistance slopes DOWN and the last candle closes above it; support slopes UP and the last candle closes below. (2) Labels don't overlap candles. (3) 3 tags visible without clipping. (4) EMA on the correct side of the last close.

Never use `analyze()`'s return at the final bar alone — that only gives you the most recent cross, which is often 0 (no signal). The replay loop is the only way to get historical signal density for chart testing.

## Signal bot vs paper-trade engine

- `~/tredalgo_signal_bot.py` (this skill): signal-alert only, no orders, Delta REST candles, PNG charts to Telegram.
- `~/paper_trade/engine.py` (paper-trade-simulator skill): stateful paper trader, `state_v2.json`, actually simulates equity/trades.
- `~/paper_trade/tredalgo_bot.py`: Telegram dashboard UI over the paper-trade engine.

These three do not talk to each other. Deploying one does not affect the others.
