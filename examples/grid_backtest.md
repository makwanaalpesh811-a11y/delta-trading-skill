# Grid Backtest — Example

## Copy-paste

```bash
# Run grid backtest with mock data
python3 grid_backtest.py --symbol ADA --period 6m --grids 15 --dry-run
```

## Expected Output

```
Strategy: Grid
Symbol: ADA
Period: 6m
Grids: 15
Trades: 42
Profit factor: 1.175
Max drawdown: -8.3%
Mode: DRY-RUN (no live execution)
```

## Safety

- Requires backtest data CSV (public data OK)
- No API keys needed for backtest
- Output is analysis only, not executable orders
