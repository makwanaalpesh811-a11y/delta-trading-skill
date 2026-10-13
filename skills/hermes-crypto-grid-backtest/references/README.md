# Hermes Crypto Grid Backtester

Ye Hermes skill ka **actual working implementation** hai — sirf **crypto** ke liye
(forex/stocks hata diya gaya hai, jaisa aapne bola). Isme Python se jo strategy
banegi wahi Pine Script me export ho sakti hai (same logic, same parameters) —
taaki backtest me jo setup best nikle, wahi live/webhook pipeline me use ho, alag
se dobara code na likhna pade.

## Kya karta hai

1. Aapke crypto OHLCV CSV data ko load karta hai (per symbol + per timeframe).
2. **Grid backtest** chalata hai — EMA fast/slow, RSI period/buy/sell, ATR
   period, stop/target ATR-multiple, cooldown — sab grid dimensions hain, jaisa
   aapne bola tha (multiple markets → multiple timeframes → multiple values).
3. Har combination ke liye trades count, win rate, profit factor, drawdown,
   Sharpe, aur **trades/day** calculate karta hai.
4. Screening: kam se kam 100 trades chahiye reliable ranking ke liye (kam ho to
   result rakhta hai par `low_sample` flag laga deta hai — discard nahi karta).
   Date range: **last 365 din, ya jitna data available hai** (jo bhi kam ho).
5. Ranking me **2-3 trades/din** wale combos ko priority deta hai — agar koi
   combo us band me na aaye, to nearest wale dikhata hai (silently range nahi
   badalta).
6. Har symbol ke liye alag **Top 10**, plus ek **global Top 10** sabhi symbols
   milaake.
7. Winning config ko `selected_strategy_config_<SYMBOL>.json` me save karta hai
   — isi file se `pine_export.py` Pine Script bana deta hai.

## Strategy jo backtest ho rahi hai (base variant)

- **Long**: EMA(fast) EMA(slow) ko upar cross kare (golden cross) AND
  RSI > `rsi_buy` (momentum confirm)
- **Short**: EMA(fast) EMA(slow) ko neeche cross kare (death cross) AND
  RSI < `rsi_sell`
- **Stop-loss / Target**: entry price se `stop_atr` / `target_atr` × ATR door
  (ab grid me 5×5 = 25 SL/TP combos, `target_atr > stop_atr` constraint ke
  saath — SL se chhota TP wale combos test hi nahi hote)
- Ek time pe sirf ek open position, `cooldown_bars` tak next entry nahi

## Max drawdown plan gate

- `screening.max_drawdown_pct` (config me, default **0.20** = 20%) — jis bhi
  combo ka max drawdown isse zyada nikle, wo gate `max_drawdown_exceeded` ke
  saath fail ho jaata hai (result `all_trials.csv` me rehta hai, discard nahi
  hota, sirf gate_status me flag lag jaata hai — `top10`/`selected_strategy`
  me nahi jaayega).
- Pehle ye hardcoded 60% tha ("explosive_drawdown"); ab plan ke hisaab se
  **20%** hai aur config se change kar sakte ho.

(Note: pehle EMA-trend + RSI-oversold-bounce wala combo try kiya tha, par woh
practically kabhi trigger nahi hota — trend aur opposite-extreme RSI ek doosre
ko cancel kar dete hain. Isliye crossover+momentum wala version use kiya, jisme
same sabhi parameters use hote hain par actually trades produce karta hai.)

## Setup (Pydroid3 / Termux)

```bash
pip install pandas numpy pyyaml tabulate --break-system-packages
```

## Apna data daalo

Har symbol+timeframe ke liye ek CSV chahiye, is naam se:

```
data/BTCUSDT_1h.csv
data/ETHUSDT_15m.csv
```

Columns (header row me, case-insensitive): `timestamp, open, high, low, close, volume`

`example_data/` folder me do **synthetic (fake, random-walk) CSVs** diye hain —
sirf format samjhane ke liye aur code test karne ke liye. **Ye real market data
nahi hai** — apna asli data (Delta Exchange India se export/API se) isi format
me `data/` folder me daalo.

## Chalane ka tarika

**Pehle ek chhota test run** (2 symbols, 1 timeframe, 8 combos — kuch second me
khatam ho jaayega, sirf pipeline check karne ke liye):

```bash
python run_grid_backtest.py --config quick_test_config.yaml --data-dir example_data --out outputs
```

**Fir asli full grid** (apna data-dir aur config edit karke):

```bash
python run_grid_backtest.py --config grid_config.yaml --data-dir data --out outputs
```

`grid_config.yaml` me symbols/timeframes/parameter grids edit kar sakte ho.

### ⚠️ Runtime ka andaza — important

`grid_config.yaml` jaisa hai waisa hi chalaya to (SL/TP grid ab 5×5 hai, aur
`target_atr > stop_atr` constraint laga hai):
- 2 symbols × 3 timeframes × **7290 valid combos** = **~43,700 backtest trials**
- Is sandbox pe benchmark: ~0.015 sec/trial (1h candles, 365 din). 15m pe ~10x
  zyada bars hone se ~10x zyada time lagega.
- **Total andaza: ~40-70 minute** is machine pe. Phone (Termux/Pydroid3) par
  CPU slower hone se **2-3+ ghante** lag sakte hain.

Suggestion: pehle kam symbols/timeframes/grid values se chalao (jaise sirf
BTCUSDT, sirf 1h, chhoti grid), result dekho, fir dheere-dheere grid badhao.
Termux me lambe run ke liye `nohup python run_grid_backtest.py ... &` use karo
taaki app band karne pe bhi chalta rahe.

## Output files (`outputs/` folder me)

- `all_trials.csv` — har trial (jeetne wale + haarne wale sab)
- `top10_<SYMBOL>.csv` — har symbol ka apna Top 10
- `top10_global.csv` — sabhi symbols milaake global Top 10
- `selected_strategy_config_<SYMBOL>.json` — har symbol ke #1 combo ka poora
  reproducible config (yehi Pine export ke liye use hoga)
- `trade_log_<hash>.csv` — us #1 combo ke saare individual trades
- `run_manifest.json` — run ki poori detail + saare assumptions
- `failure_log.csv` — jo combos gate fail hue (0 trades, ya negative net, etc.)
- `report.md` — sab kuch ek human-readable report me

## Pine Script me export (live/paper ke liye)

```bash
python pine_export.py outputs/selected_strategy_config_BTCUSDT.json > BTCUSDT_hermes.pine
```

Ye same EMA-cross + RSI + ATR-stop/target logic wali Pine v5 strategy banata
hai — same numbers, same threshold, koi manual re-typing nahi. Isko TradingView
me paste karke apne webhook → Delta Exchange pipeline se connect kar sakte ho.

## Yaad rakhne wali baatein

- Ye sirf **hypothetical research** hai — koi real order kabhi place/modify
  nahi hota. Real fills real backtest se thoda alag ho sakte hain.
- 2-3 trades/din ek **preferred target** hai, guarantee nahi — agar strategy ki
  nature (jaise 1h EMA-crossover) itni frequency naturally nahi deti, to
  "nearest" combos dikhaye jaayenge, band forcefully nahi todi jaayegi.
- `all_trials.csv` me low-frequency ya low-sample combos bhi rehte hain (delete
  nahi hote) — sirf `low_sample`/gate flags lag jaate hain, taaki koi result
  chhupa na ho.
