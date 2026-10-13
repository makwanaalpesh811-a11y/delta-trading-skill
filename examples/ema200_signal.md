# EMA200 Trendline Signal — Example

## Copy-paste

```bash
# Fetch candles + run signal (read-only, no orders)
python3 ~/ema_tl_signal.py --symbol NIFTY --timeframe 15m --dry-run
```

## Expected Output

```
Symbol: NIFTY
Timeframe: 15m
Price: 24532.4
EMA200: 24401.7
Trend: BULLISH (price > EMA200)
Signal: LONG ✓
SL: 24450 (-0.34%)
TP: 24620 (+0.36%)
Mode: DRY-RUN (no orders placed)
```

## Safety

- Defaults to `read` mode (MCP config)
- Dry-run by default
- Never places orders without explicit confirmation
