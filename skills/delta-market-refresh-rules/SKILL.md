---
name: delta-market-refresh-rules
description: "Refresh loop rules for market-data only."
---
Always-on (never disabled): no live trading/orders; DELTA_MCP_MODE=trade never; DELTA_API_KEY never exposed; no fabricated data; no backtest rule mutation; bounded chunks for historical downloads.
Loop rules (market-data refresh/monitoring only): (1) User-explicit loop allowed. (2) Default max-speed, configurable interval, user max iterations/duration. (3) If user asks "infinite loop" / "jab tak rokoon": before start clearly say — refresh continuous; must give stop/cancel command to halt; risk CPU/API rate-limit/data cost. (4) Continuous refresh only after explicit user confirmation. (5) Rate-limit/timeout/resource/API safety maintained. (6) Scope: market-data refresh only. (7) Non-disableable: no trading, no trade mode, no credential exposure, no fabricated data, no backtest change. (8) Backtest historical: bounded chunks + reproducible files.
Behavior: "max speed refresh" → fast bounded configurable refresh; "continuous refresh" → runs after user confirm; "stop refresh" → halt loop, show final status.
