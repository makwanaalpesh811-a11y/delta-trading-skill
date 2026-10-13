---
name: forex-news
description: "Forex Factory News"
version: 1.0.0
author: Alpesh Makwana
license: MIT
platforms: [linux]
---

name: forex-news
description: Use when user sends /news or /ff for Forex Factory events.
version: 1.1.0
author: Alpesh Makwana
license: MIT
platforms: [linux, macos]
---

# Forex Factory News

Trigger words (case-insensitive): `/news`, `/ff`, `/forex`, `forex news`, `ff news`, `news`

## Scripts

Two scripts available:

1. `~/forex_ff/ff_news.py` — English output
2. `~/forex_ff/ff_news_gj.py` — Gujarati output (default for this user)

User is Gujarati speaker. Use the Gujarati script by default.

## Action

Run based on trigger:

```bash
# Default (Gujarati, 24h, with ETH impact):
python3 ~/forex_ff/ff_news_gj.py 24

# Custom hours:
python3 ~/forex_ff/ff_news_gj.py 48

# English output:
python3 ~/forex_ff/ff_news.py 24
```

Return the script's stdout VERBATIM. Do NOT reformat or add commentary unless the user asks.

## Behavior rules

1. Default to Gujarati script
2. Default window is 24 hours
3. If user asks for a specific country (e.g. `news usd`), filter the JSON for `country='USD'`
4. If user asks for high impact only, filter for `impact='High'`
5. All times shown in IST (UTC+5:30) automatically
6. ETH impact assessment is automatic per event

## Data source

URL: `https://nfs.faireconomy.media/ff_calendar_thisweek.json` (Forex Factory public feed, no API key needed)

## Extended examples

```
news          → python3 ~/forex_ff/ff_news_gj.py 24
news 48       → python3 ~/forex_ff/ff_news_gj.py 48
ff            → same as news
news usd      → filter for USD events
news gold     → filter for XAU-related (USD) events
news english  → use ff_news.py instead
```

## Fallback if script missing

```
curl -s https://nfs.faireconomy.media/ff_calendar_thisweek.json | jq '.[] | select(.impact=="High") | {date, country, title}'
```

## User preferences

- User (Alpesh) is Gujarati-speaking, IST timezone
- Wants ETH impact assessment per event (🔴🟡⚪)
- Wants F (Forecast) and P (Previous) shown for each event
- Times in IST format
