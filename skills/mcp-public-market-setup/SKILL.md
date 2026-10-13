---
name: mcp-public-market-setup
description: "Public MCP setup with no keys and no trade mode."
---

# MCP Public-Market Setup (Read-Only)

Always-on rules: no DELTA_API_KEY/DELTA_API_SECRET; never DELTA_MCP_MODE=trade; backup config; only public-market tools; safe install fallback when uv missing. On Android aarch64: prefer `pip install uv` binary-only; if `--only-binary :all:` fails (pip tag mismatch), do not force unsupported binary — stop and confirm.

Procedure: verify Python>=3.12; check uv/uvx; safe uvx or pip install; Hermes mcp_servers entry with empty env; backup config.yaml; verify public-market tests; confirm no keys, no mutations.

Support files:
- `references/termux-mcp-and-claude-code.md` — Termux MCP install/run (`pip install termux-mcp`, `termux-native-mcp` on :8081) and why `@anthropic-ai/claude-code` won't run on Termux (no linux-arm64-android binary). Also the 2026 Colab auth API status: `authenticate_user()` is the only surviving method, and `run_console`/`run_local_server`/`get_user_credentials` are all removed.
- `references/hermes-manus-collab.md` — Hermes + cloud AI (Manus, Genspark) multi-Gmail collaboration via a shared `~/Hermes_Almari/99_COLLABORATION/` state directory, when the user rotates Google accounts to multiply per-Gmail credit limits.
- `templates/manus_master_prompt.txt` — drop-in prompt to paste at the start of each cloud session so it re-loads shared state.
- `templates/start_collab.sh` — start/status/stop wrapper for `termux-native-mcp` + `localhost.run` SSH tunnel on mobile data.
