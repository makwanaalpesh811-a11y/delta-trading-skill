# ⚡ Delta Exchange Trading Skill

Delta India exchange - market data, signals, paper trade, live orders, backtesting

**Repository by:** [Alpesh Makwana](https://github.com/makwanaalpesh811-a11y)

---

## 📦 What's Inside

14 Hermes Agent skills for delta exchange trading skill:

- `delta-live-order-execution` — "Place Delta v2 orders. HMAC-signed, dry-run default."
---

# Delta Live Order Execution

Placing...
- `delta-market-refresh-rules` — "Refresh loop rules for market-data only."
---
Always-on (never disabled): no live trading/orders...
- `delta-mcp-india-readonly` — "Delta Exchange MCP setup. Read-only market data only."
---
Always-on gates: no API key saved; DE...
- `delta-tick-candles` — "Stream Delta tick CSVs to M1 candles. Phone-storage data."
---

# Delta Tick -> M1 Candles

User...
- `ema200-trendline-signal` — Fetch fresh Delta MCP candles and run the 15m signal script.
---

# EMA200 + TrendLine Break Sign...
- `forex-news` — Use when user sends /news or /ff for Forex Factory events.
- `hermes-crypto-grid-backtest` — Grid backtest crypto OHLCV, rank combos, export Pine.
- `hyperliquid` — Hyperliquid market data, account history, trade review.
- `mcp-public-market-setup` — "Public MCP setup with no keys and no trade mode."
---

# MCP Public-Market Setup (Read-Only)

Al...
- `paper-trade-simulator` — Use for 24/7 crypto paper-trade simulator on Termux. Trigger word 'tredalgo' or 'trading algo' = ...
- `signal-bot-matplotlib` — Use for ~/signal_bot.py — matplotlib Delta bot.
- `stocks` — Stock quotes, history, search, compare, crypto via Yahoo.
- `strategy-backtest-verify` — Use before grid/param sweep on a user-provided strategy.
- `tredalgo-signal-bot` — Maintain tredalgo_signal_bot.py — Pine-style PNG chart bot.

---


## 🔐 SECURITY NOTICE

**This repo is safe to use publicly.** It contains only skill definitions (SKILL.md) and documentation - no live credentials.

### What NOT to commit:
- API keys (GitHub, YouTube, Gemini, OpenAI, etc.)
- AWS credentials (`~/.aws/credentials`)
- Telegram bot tokens
- Exchange API keys (Delta, Hyperliquid, etc.)
- Private keys or certificates

### Where to store secrets (on your machine):
```
~/.aws/credentials          # AWS
~/.youtube_token.json       # YouTube OAuth
~/.ig_env                   # Instagram/Gemini
~/.signal_bot_env           # Trading bot
~/.gh_token                 # GitHub token
```

All skills are designed to read secrets from your filesystem, not embed them.


## 🚀 Installation

### Option 1: Clone to Hermes skills directory
```bash
git clone https://github.com/makwanaalpesh811-a11y/delta-trading-skill.git ~/.hermes/skills/delta-trading-skill
```

### Option 2: Install individual skills
```bash
# Create skills dir if not exists
mkdir -p ~/.hermes/skills

# Clone only what you need
git clone --depth 1 --filter=blob:none https://github.com/makwanaalpesh811-a11y/delta-trading-skill.git /tmp/delta-trading-skill
cp -r /tmp/delta-trading-skill/skills/* ~/.hermes/skills/
```

---

## ⚙️ Prerequisites

Check each skill's `SKILL.md` for specific dependencies. Common ones:
- **Termux** (Android terminal) or Linux/macOS
- **Python 3.11+**
- **Node.js + npm** (for CLI-based skills)
- **API keys** stored in `~/.<name>_env` or `~/.<name>_token.json` files

---

## 🔧 Setup Guide

1. **Install Hermes Agent:** `pip install hermes-agent` or see [Hermes docs](https://hermes-agent.nousresearch.com/docs)
2. **Clone this repo** into `~/.hermes/skills/`
3. **Configure credentials** in your environment (see each skill's SKILL.md)
4. **Use in chat:** Ask Hermes to use any skill by name

---

## 📚 Skill Documentation

Each skill lives in `skills/<skill-name>/SKILL.md` with:
- **YAML frontmatter:** name, description
- **Commands:** CLI/API references
- **Examples:** Ready-to-use snippets
- **Gotchas:** Real-world pitfalls

---

## 🛡️ Security

## 🔐 SECURITY NOTICE

**This repo is safe to use publicly.** It contains only skill definitions (SKILL.md) and documentation - no live credentials.

### What NOT to commit:
- API keys (GitHub, YouTube, Gemini, OpenAI, etc.)
- AWS credentials (`~/.aws/credentials`)
- Telegram bot tokens
- Exchange API keys (Delta, Hyperliquid, etc.)
- Private keys or certificates

### Where to store secrets (on your machine):
```
~/.aws/credentials          # AWS
~/.youtube_token.json       # YouTube OAuth
~/.ig_env                   # Instagram/Gemini
~/.signal_bot_env           # Trading bot
~/.gh_token                 # GitHub token
```

All skills are designed to read secrets from your filesystem, not embed them.

---

## 📜 License

MIT License - see [LICENSE](./LICENSE)

---

## 👨‍💻 Author

**Alpesh Makwana** — Trading, content, and Hermes Agent enthusiast.

- **GitHub:** [makwanaalpesh811-a11y](https://github.com/makwanaalpesh811-a11y)
- **Telegram:** @alpeshalgobot

---

## 🤝 Contributing

Issues and PRs welcome. Follow the SKILL.md format conventions.

## 🏷️ Topics
`delta-exchange` `crypto` `options` `trading` 
