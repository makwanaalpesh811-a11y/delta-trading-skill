# Chart annotation — overlay V2 levels on a trading screenshot

Use when user shares a chart screenshot and asks to "do V2 strategy" / "mark SL TP" / "annotate" / "photo me dikhao". Overlay the strategy levels (EMA300, trendlines, SL/TP, current price) as a colored JPEG so the user can read it on their phone without re-reading the raw numbers.

## Pipeline

1. **Fetch fresh candles** for the symbol in the screenshot (Delta India 1h, 500 bars).
2. **Compute the V2 state** — EMA300, ATR14×1.5 SL, RR 3.0 TP, pivot(3,3) trendlines.
3. **Derive price levels** for the annotation (current, EMA, up/down trendline extrapolated to the latest bar, LONG and SHORT setup entry/SL/TP).
4. **Map price → pixel Y** using the chart's top/bottom reference prices. Get these from a `vision_analyze` on the original screenshot, or sample the price-axis labels.
5. **Draw with PIL** on a copy of the original image: dashed trendlines, solid EMA, boxes for LONG/SHORT setups, a banner with the signal verdict.
6. **Save to `/sdcard/Hermes_FFiles/uploads/`** so the user sees it in Hermes Files UI. Send as `MEDIA:` in the reply.

## Price → Y mapping

```python
# Given two reference prices (top and bottom of visible chart), and their pixel Y:
# y = y_top + (price_top - price) * (y_bottom - y_top) / (price_top - price_bottom)
#
# Example (ETHUSD photo, 576x1280 image, candle area y=200..800):
#   price 3040 at y=200, price 2200 at y=800
#   def py(price): return int(200 + (3040 - price) * 600.0 / 840.0)
```

To find the reference prices: read the price-axis labels on the right side of the screenshot (top label = highest visible price, bottom label = lowest). Do NOT assume from the visible candle extents — the axis range is wider than the candles.

## PIL setup on Termux

```bash
pkg install -y python-pillow   # NOT pip install Pillow
```

Font paths that work on Termux Android:
```python
from PIL import ImageFont
font_big = ImageFont.truetype('/system/fonts/DroidSans-Bold.ttf', 22)
font_mid = ImageFont.truetype('/system/fonts/DroidSans-Bold.ttf', 16)
font_sm  = ImageFont.truetype('/system/fonts/DroidSans.ttf', 13)
```

`/system/fonts/NotoSans-*.ttf` usually does NOT exist on standard Termux Android — use `DroidSans`. Wrap in try/except with `ImageFont.load_default()` fallback so a font path change doesn't break the whole run.

Open the image with `.convert('RGB')` before drawing RGBA overlays: `ImageDraw.Draw(im, 'RGBA')` accepts tuple-with-alpha fills and blends correctly against the RGB base. Without `.convert('RGB')`, saving back to JPEG throws a mode error.

## Color conventions (match the dashboard's green/red)

- Current close → yellow box `(255, 220, 0, 220)` — the anchor, always visible
- EMA300 → white solid `(255, 255, 255, 200)`, width 2 — matches the platform's white line
- Up trendline → green dashed `(80, 220, 80, 220)` — LONG trigger
- Down trendline → red dashed `(255, 80, 80, 220)` — SHORT trigger
- Support → blue `(100, 150, 255, 200)` solid thin
- Resistance → orange `(255, 200, 100, 200)` solid thin
- LONG setup box outline green, SL text red, TP text green
- SHORT setup box outline red, SL text yellow, TP text red

Labels sit just outside the chart-right edge (x = `CHART_RIGHT + 5`) so they don't cover candles. Keep them short — `EMA300 2639`, `UP TL 2668`, `CLOSE 2648`.

## Setup boxes

Draw two bordered rectangles covering the entry→SL→TP range of each setup. Label each box with three lines:
- Top: trigger condition (`LONG IF BREAK` above UP TL, or `SHORT IF BREAK` below EMA)
- Middle: TP price (colored by direction)
- Bottom: SL price (colored by direction, opposite to TP)

Position the labels so they don't overlap the box borders — offset `py(TP) - 30` for the header, `py(TP) - 12` for TP, `py(TP) + 8` for entry, `py(SL) - 4` for SL. If the two setup boxes overlap vertically, place the SHORT labels on the left column (x offset negative) so they don't fight the LONG labels.

## Signal verdict banner

Top strip (y=0..60, full width, black with 220 alpha) with two lines:
- Line 1: `{STRATEGY NAME} — {SYMBOL} {TF}` in yellow, font_big
- Line 2: `{SIGNAL} — {reason}` in white, font_mid

Bottom strip (y=990..1130, left column only, black 220 alpha) with the numeric legend: signal, up/down TL, ATR, SL/TP distances, trigger conditions. Keep this BELOW the chart candles but ABOVE the platform's own Long/Short buttons (usually y>1130) so it doesn't cover the UI.

## Pitfalls

- **NEUTRAL signal needs explicit visual treatment.** When close is trapped between EMA and UP TL (or EMA and DOWN TL), don't just show the levels — draw BOTH the LONG and SHORT setup boxes with `IF BREAK` labels so the user sees exactly what would flip the signal. A neutral verdict without the trigger levels just says "wait" with no actionable info.
- **The white line on the chart is EMA300, not EMA200.** Delta's UI labels it "EMA 300 close 0" in the top bar. If the annotation overlays a different EMA than the platform shows, the user will read the mismatch and lose trust.
- **Trendline extrapolation can land outside the visible range.** After `p2[1] + slope * (latest_i - p2[0])`, the projected trendline value may be above the visible price axis. Check it's within `[price_bottom, price_top]` before drawing — if outside, either clamp the label to the chart edge or skip the trendline (state is probably "broken" anyway).
- **The chart x-range is usually narrower than the image width.** Mobile trading UIs put the order book on the right side of the chart. Set `CHART_RIGHT` to the left edge of the order book, not the image width — otherwise the level lines run under the order book and the labels collide with it.
- **`vision_analyze` returns approximate pixel coordinates.** Treat them as ballpark, then sample the actual image with PIL to find the chart-axis boundaries. Do not hardcode y=480 without verifying — the screenshot resolution varies by device.
- **Save to `/sdcard/Hermes_FFiles/uploads/`, not `~/paper_trade/`.** Files outside the uploads folder do not appear in Hermes Files UI. The annotated chart is the user-facing artifact.
- **Don't annotate the order book column.** The right side of the chart is live order book data — overlaying strategy lines there is noisy and misleading. Stop all lines at `CHART_RIGHT`.
- **JPEG quality 92, not 95+.** Higher quality balloons file size for no visible gain on phone screens; 92 fits under the 100KB range easily and reads fine.
