---
name: delta-tick-candles
description: "Delta Tick -> M1 Candles"
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux]
---

name: delta-tick-candles
version: 1.0.0
description: "Stream Delta tick CSVs to M1 candles. Phone-storage data."
author: Alpesh Makwana
license: MIT
platforms: [linux, macos]
---

# Delta Tick -> M1 Candles

User's real tick-level OHLCV lives on phone external storage or the Almari, NOT in the home JSON caches. Extracted CSVs are the source of truth; ZIP archives in `Download/` must be unzipped first. The JSON files under `~/delta_candles/*.json` and `~/candles_*.json` are older/smaller subsets and shouldn't be the source of truth for a backtest the user is asking for now.

When the user says 'Hermes file' or 'Delta data' without further context, they mean the Almari/phone-storage CSVs, not the home-dir JSON caches. Confirm which months + which product (ETHUSD futures vs ETH options, ETH vs ADA) before loading.

## Data Layout

Primary source (largest tick corpus, already extracted):

```
/sdcard/Hermes_Almari/02_DATA/ada_ticks_extracted/<month_dir>/ADAUSD_YYYY-MM.csv   # ADA futures (e.g. Jan-Sep 2026, 843k ticks)
/sdcard/Hermes_FFiles/delta_data/extracted/ETHUSD_YYYY-MM.csv   # ETH futures, ~7M ticks/mo
/sdcard/Hermes_FFiles/delta_data/extracted/ETH_YYYY-MM.csv       # ETH options
```

Fallback source (fresh archives the user drops in Almari Downloads):

```
/sdcard/Hermes_Almari/Download/futures-trades-monthly-<SYM>-<YYYY-MM>_<id>.csv    # ZIP archives (PK header), NOT CSV
```

These `Download/futures-trades-monthly-*` files are ZIP archives despite the `.csv` extension — `unzip -o <file> -d <dir>` extracts the real CSV. `file <path>` on Termux usually errors out; check the first bytes are `PK\x03\x04` (or use `head -c 4 <file> | xxd`) instead. After extracting, move to a stable extracted dir so re-runs are cheap.

## CSV Format (tick-level)

Header: `product_symbol,price,size,timestamp,buyer_role`

Sample rows:
```
ETHUSD,2970.9,36.0,2026-01-01 00:00:01.502604,maker
ETHUSD,2971.2,109.0,2026-01-01 00:00:01.828044,taker
```

Key: timestamp is `%Y-%m-%d %H:%M:%S.%f`, UTC assumed. `buyer_role` is `maker`/`taker` — taker buys count as positive volume.

A single month has 5-7 million ticks (7M in Jan 2026). Never load a month into memory as a single list — stream it line by line and aggregate to M1 as you go.

## Aggregation Recipe

Stream-read each month's CSV. For every row:

```python
import csv, json
from datetime import datetime, timezone
from collections import OrderedDict

def aggregate_1m(csv_path):
    candles = OrderedDict()
    with open(csv_path) as f:
        next(f)  # header
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 5: continue
            price = float(parts[1])
            size  = float(parts[2])
            ts    = parts[3]
            role  = parts[4]
            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
            minute_ts = int(dt.timestamp()) - int(dt.timestamp() % 60)
            if minute_ts not in candles:
                candles[minute_ts] = {'time': minute_ts, 'open': price, 'high': price,
                                       'low': price, 'close': price, 'volume': size,
                                       'taker_buy_vol': size if role == 'taker' else 0.0}
            else:
                c = candles[minute_ts]
                c['high']  = max(c['high'], price)
                c['low']   = min(c['low'], price)
                c['close'] = price
                c['volume'] += size
                if role == 'taker': c['taker_buy_vol'] += size
    return list(candles.values())
```

Produces a JSON list of M1 candles: `[{time, open, high, low, close, volume, taker_buy_vol}, ...]`. `time` is epoch seconds floored to the minute.

## Multi-Month

Loop over months, extend one list, sort by time, save once:

```python
all_candles = []
for m in ['2026-01', '2026-02', ...]:
    all_candles.extend(aggregate_1m(f'/sdcard/Hermes_FFiles/delta_data/extracted/ETHUSD_{m}.csv'))
all_candles.sort(key=lambda c: c['time'])
```

8 months of ETHUSD ≈ 56M ticks ≈ 28-30 min on Termux. Run background.

## M1 → M3 / M15 / Any-N-Minute (pandas resample)

Once M1 is built, derive coarser TFs with pandas — do NOT re-scan ticks for each TF (30x slower and duplicative):

```python
import pandas as pd, numpy as np

def to_tf(df_m1, minutes, out_path):
    df = df_m1.copy()
    df['dt'] = pd.to_datetime(df['time'], unit='s', utc=True)
    out = (df.set_index('dt').resample(f'{minutes}min', closed='left', label='left')
              .agg(open=('open','first'), high=('high','max'),
                   low=('low','min'),  close=('close','last'),
                   volume=('volume','sum')).reset_index())
    out = out.dropna(subset=['open'])
    out = out[out['open'] > 0]              # drop empty buckets
    # CRITICAL: pandas 3.0 stores datetime64 as microseconds; astype('int64') // 10**9 yields 1000x too small
    out['time'] = out['dt'].apply(lambda x: int(x.timestamp()))
    out[['time','open','high','low','close','volume']].to_csv(out_path, index=False)
```

Sanity check the first timestamp: it should be in the range ~1.75e9 to ~1.78e9 for 2025-2026 data. If you see ~1.77e6, you are 1000x off — pandas picked microsecond resolution and your divisor was wrong.

Reference sizes (ADAUSD Jan-Sep 2026, 843k ticks): M1 = 178k rows / 8.5 MB; M3 = 91k / 4.4 MB; M15 = 22k / 1.1 MB. Build M1 first, then M3 and M15 resample in seconds.

## Fixed SL/TP % Grid Backtest (EMA-cross strategies)

When the user wants a % SL/TP sweep instead of ATR-based stops (e.g. '0.5% SL / 1% TP'), run a grid over `sl_pct × tp_pct × tf`. Same shape as ATR grid backtests but simpler — no indicator math beyond EMA:

```python
# signal: close > EMA → LONG, close < EMA → SHORT (fresh cross only)
# SL/TP: entry*(1 ± sl_pct), entry*(1 ± tp_pct)
# scan forward max ~500 candles; first hit wins; tie → OPEN
# PF = GP_R / GL_R where GP_R = wins * (tp_dist / sl_dist), GL_R = losses * 1
# Train/Test 70/30; rank by min(train_pf, test_pf)
```

Key notes:
- **Compute EMA over the FULL series once, then scan signals** — never recompute per candidate row.
- **Rank by `min(train_pf, test_pf)`**, not `test_pf` alone. Cross-TF consistency (15m > 3m > 1m for the same combo) is a healthy sanity signal; the reverse usually means overfit on higher-freq noise.
- **Higher RR (TP/SL ratio) → higher PF but fewer TP hits.** On ADAUSD 15m, SL=1% TP=6% landed the top MinPF (~16.8x); 1m at 6% TP fell off as expected.
- **PF is R-multiple clean but equity-compounding math is easy to botch.** If PF ≥ 10x but equity still bleeds in `ret`, verify the compounding loop applies `(tp-entry)/entry * 100 * side / 100` to equity — not the raw R. Report PF, WR, and `ret` separately so the user can tell them apart.
- **Grid is cheap on these TFs:** 6 SL × 7 TP × 3 TF = 96 combos × ~500-candle scan = ~60s on Termux once candles are built. Run foreground.

## Feed into Existing Backtesters

- `hermes-crypto-grid-backtest` expects `SYMBOL_TIMEFRAME.csv` with header `timestamp,open,high,low,close,volume` under `--data-dir`. Convert the aggregated JSON to that CSV format before running the grid.
- Custom Pine-script ports: pass the aggregated M1 list directly to any Python strategy loop that expects `[{time, open, high, low, close, volume}, ...]`.

## Pitfalls

- **pandas 3.0 datetime64 is microseconds, not nanoseconds.** `.astype('int64') // 10**9` produces timestamps 1000x too small (renders as 1970). Convert via `.apply(lambda x: int(x.timestamp()))` or check the pandas version and adjust the divisor. On Termux `pkg install python-pandas` gives pandas 3.0.6+, where the broken formula fails silently — candles get written, but every time stamp is a 1970 date that only shows up when you format it for display.
- **Never re-scan ticks per timeframe.** M1 is the source; M3/M15 come from resampling M1 (~30x faster, no risk of divergence).
- **Phone storage is not in the home dir.** `/sdcard/Hermes_Almari/` and `/sdcard/Hermes_FFiles/` are real, separate from `~/.hermes/`. `find ~ -name 'delta*'` will miss them. Ask the user or `ls /sdcard/Hermes_Almari/02_DATA/` and `ls /sdcard/Hermes_Almari/Download/` explicitly.
- **`futures-trades-monthly-*` files are ZIPs, not CSVs.** Header bytes are `PK\x03\x04`. `head`/`cat` shows binary garbage — `unzip -o <path> -d <extract_dir>` first, then read the real CSV inside. `file(1)` may be missing on Termux; use `head -c 4 <file>` + `xxd`.
- **Never `json.load` a raw tick CSV.** 500MB single file. Stream with `for line in f: line.split(',')` or use `pd.read_csv` on the extracted files (multi-hundred-k row files load fine once unzipped).
- **Timestamps parse as naive local, then assume UTC.** `datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')` then `replace(tzinfo=timezone.utc)`. Don't call `datetime.fromtimestamp()` on the raw string — it misinterprets the offset on some systems. Pandas path: `pd.to_datetime(col)` then `.astype('int64') // 10**9` for unix seconds.
- **Options CSVs (`ETH_YYYY-MM.csv`) are 5-10x smaller than futures** because they only contain option contract trades, not the underlying. Use `ETHUSD_*` / `ADAUSD_*` for price action, `ETH_*` for option premium/OI work.
- **Taker-only volume is the meaningful signal.** Summing `volume` counts makers too (passive fills), which inflates bars during maker-heavy quiet periods. Track `taker_buy_vol` separately and prefer it for order-flow filters.
- **Delta has both maker and taker on the same tick.** A single tick can appear twice with different roles if both sides of the book fill — the aggregation loop must treat each row independently.
- **Duplicate month dirs can appear** when the user re-downloads a month (two `2026-06` folders). Concat + sort handles it, but `wc -l` before assuming totals are right.
- **Build M1 first, then resample to M3/M15 — don't re-scan ticks for each TF.** Pandas resample is ~30× faster than re-streaming.
- **Run 1m aggregation in the background.** 8 months at 250-500MB each means 10-15 min of CPU even with streaming. `nohup python3 script.py > log 2>&1 &` or the terminal background flag with notify. 3m/15m resample from M1 is under 10s each.

## Verification

After aggregation, sanity-check:
- Total M1 candles ≈ (months × ~43800) — one month of minutes is 43200; a real month is ~44000.
- First candle close ≈ last candle close of the previous month (small gap for maintenance windows).
- Spot check 3 random minute timestamps against the CSV: filter CSV rows for `HH:MM:` and verify OHLC matches.

## Safety

Data is read-only from phone storage. Aggregated JSON stays under the home dir for backtest consumption. No trade, no credentials, no Delta API keys.