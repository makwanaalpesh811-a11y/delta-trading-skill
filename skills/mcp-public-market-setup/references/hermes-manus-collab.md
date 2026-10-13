# Hermes + Manus (multi-Gmail) Collaboration via Shared Almari

Reusable pattern when the user wants Hermes (this agent, running on Termux) and a cloud AI assistant (e.g. Manus with a 300-credit/day limit per Gmail) to coordinate on tasks, and the user plans to rotate through multiple Google accounts to multiply available credits.

The idea: neither side talks to the other directly. They share a **state directory on Termux** that both read and write through MCP, and each cloud session starts by loading that state so it picks up exactly where the previous one left off.

## When to use this

Use when ALL of these are true:

- User has a second cloud AI (Manus, Genspark, GPT-4, etc.) they want to contribute to the same work as Hermes
- User has a per-Gmail credit/quota limit and plans to use multiple accounts
- User wants continuity across sessions (the second AI must not start from scratch)
- Hermes can reach Termux, and the second AI can reach Termux MCP

Skip this when a single AI handles the task end-to-end, or when the second AI does not have MCP tool access.

## Shared state directory

Create `~/Hermes_Almari/99_COLLABORATION/` on Termux with this layout:

```
99_COLLABORATION/
├── state.json               ← single source of truth, both read
├── README.md                ← points to state.json + protocol
├── manus_master_prompt.txt  ← template to paste at start of each cloud session
├── pending/
│   └── tasks.md             ← current task list with priorities
├── manus_output/            ← cloud AI writes full solutions here
├── hermes_output/           ← Hermes writes its outputs here
├── journal/
│   └── YYYY-MM-DD.md        ← both append daily logs
├── decisions/
│   └── YYYY-MM-DD_<topic>.md
├── blockers/
│   └── YYYY-MM-DD_<topic>.md  ← when stuck, write blocker here for the other side
└── scripts/
    └── logs/                ← termux-mcp.log, tunnel.log, etc.
```

## state.json schema

Minimum fields. Keep it compact — the second AI has to read it in one MCP call.

```json
{
  "last_updated": "YYYY-MM-DD HH:MM IST",
  "current_user": "<name>",
  "user_gmail": "<email>",
  "phone_ip": "<current phone IP or note it's mobile data>",
  "tunnel_url": "https://<32hex>.lhr.life",
  "manus_mcp_url": "https://<32hex>.lhr.life/mcp",
  "active_project": "<current high-level focus>",
  "last_task": "<what was just done>",
  "next_action": "<concrete next step>",
  "status": "active | pending | blocked | done",
  "credits_today": {
    "gmail_count": 1,
    "credits_used": 0,
    "credits_left": 300
  },
  "key_env": {
    "<file_or_script>": "<path>",
    "<oauth_client>": "<client_id>",
    "<api_key>": "<redacted value or 'in ~/.file'>"
  },
  "constraints": ["<standing user preferences>"],
  "completed_today": ["<bullet>"]
}
```

Rules for updating:

- **Both sides update it after each task.** The `last_task` field is a handoff pointer; the second AI reads it first thing.
- **`status` is a boolean gate** — `blocked` means the other side should not touch that thread without a new user instruction.
- **`credits_today`** tracks the current Gmail's budget so the second AI self-limits work.
- **`blocker` block** (optional): when `status=blocked`, add a `blocker: {type, error, file, fix}` pointing to a file under `blockers/`.

## Master prompt template

Store the master prompt as a standalone file at `99_COLLABORATION/manus_master_prompt.txt` so the user can copy-paste it into any new cloud session. The prompt must do four things:

1. Tell the AI to `cat state.json` and `cat pending/tasks.md` via MCP before doing anything.
2. Give strict output rules (save to Almari, don't repeat done work, be concise, credit budget).
3. Define the exact output paths it must write to.
4. End with a **report-and-wait-for-GO** step so the user can approve before execution burns credits.

See `templates/manus_master_prompt.txt` for a ready-to-adapt version.

## Starting and checking the Termux side

Wrap the Termux MCP + tunnel startup into one script at `~/start_collab.sh` with four subcommands:

```bash
~/start_collab.sh start      # start termux-native-mcp + localhost.run SSH tunnel, write URLs to state.json
~/start_collab.sh status     # check both PIDs + POST /mcp initialize against the public URL
~/start_collab.sh restart    # stop + start
~/start_collab.sh stop       # kill both
```

Required internals:

- `termux-native-mcp --port 8081` for the MCP server
- `ssh -o StrictHostKeyChecking=no -R 80:localhost:8081 nokey@localhost.run` for public access on mobile data
- Write `mcp.pid` and `tunnel.pid` to `~/collab_mcp.pid` and `~/collab_tunnel.pid`
- Update `state.json` with the fresh tunnel URL after each start (URL changes every run)
- The `status` subcommand must POST an `initialize` JSON-RPC to the public URL and report HTTP status

See `templates/start_collab.sh` for the shell script.

## Multi-Gmail rotation workflow

Because the user rotates GMail accounts to multiply credits:

1. On GMail N, start Manus, add the Termux MCP URL as a connector, paste `manus_master_prompt.txt`, say `GO`
2. Manus reads state, reports plan, user approves
3. Manus works, saves to `manus_output/`, updates `state.json` with `credits_used`, appends journal
4. When credits run low (~50 left), user logs out, logs in with GMail N+1, pastes the same master prompt
5. New session reads state — picks up `next_action`, doesn't redo `last_task`, resumes from the journal tail

Hermes can be on the same loop — read `state.json` on session start, act on `next_action`, write back.

## Pitfalls

- **Both sides must save, not just reply.** A cloud AI that only answers in chat without writing to `manus_output/` produces zero durable work — the file write is the point.
- **Every task must touch `state.json`.** If `last_task` isn't updated, the next Gmail's session re-reads the old state and redoes the work.
- **Tunnel URL changes every start.** Never cache `manus_mcp_url` outside of `state.json` — update it on every `~/start_collab.sh start`.
- **Don't put client secrets in the master prompt.** The prompt gets pasted into chat history across many accounts. Reference secrets by file path (`in ~/.google_env`) instead of literal value.
- **`GO` gate saves credits.** Without the report-and-wait step, the second AI starts executing on turn one and burns 200 credits before the user can redirect.
- **Journal is append-only.** Both sides add entries with a timestamp; never overwrite. The tail of today's journal is the fastest way to see the last 30 minutes.
- **Mobile data = CGNAT, not Wi-Fi.** When `ip -4 addr show wlan0` returns empty, the phone is on carrier CGNAT — direct IP is unreachable, tunnel is mandatory. The `start_collab.sh` script already handles this.

## When NOT to use this pattern

- **Short-lived task.** If one session can finish in <200 credits, skip the shared state — just paste the context manually.
- **Second AI doesn't have MCP tool access.** The pattern requires both sides to be able to write files into the shared directory.
- **One-shot collaboration.** If it's a one-off "ask another AI for X" task, `delegate_task` or manual copy-paste is simpler.
