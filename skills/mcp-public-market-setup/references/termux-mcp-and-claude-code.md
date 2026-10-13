# Termux MCP + Claude Code on Termux (Android aarch64)

Two adjacent topics that came up when setting up local AI ↔ terminal bridges on Termux. Neither is delta-market-specific; both are reusable.

## Termux MCP (AI ↔ Termux terminal bridge)

**Install — pip works cleanly on Termux:**

```bash
pip install termux-mcp
```

This installs two binaries together:
- `termux-mcp` — REST API daemon on `127.0.0.1:8080` (HTTP JSON)
- `termux-native-mcp` — native MCP server (spec 2025-06-18) on `127.0.0.1:8081/mcp` for real MCP clients

**Start the native MCP server (background):**

```bash
nohup termux-native-mcp --port 8081 > ~/mcp.log 2>&1 &
```

**Auth (recommended for non-loopback access):**

```bash
export TERMUX_MCP_AUTH=***
termux-mcp token   # prints token; use as `Authorization: Bearer <token>`
```

Loopback connections default to auth-off; binding to non-loopback forces auth on.

**Client-side config (any MCP-capable AI app):**

```json
{
  "type": "http",
  "url": "http://127.0.0.1:8081/mcp",
  "commonOptions": {
    "name": "Termux",
    "enable": true,
    "headers": [["Authorization", "Bearer <TOKEN>"]]
  }
}
```

Over SSH from a desktop AI app (Cursor, Claude Desktop, VS Code):

```json
{
  "command": "ssh",
  "args": ["android", "termux-native-mcp", "--stdio"]
}
```

**Verify:**

```bash
curl http://localhost:8081/ping
curl -X POST http://localhost:8080/run -H "Content-Type: application/json" -d '{"cmd":"ls ~"}'
```

**Phone IP for remote access (Wi-Fi only):**

```bash
ip -4 addr show wlan0 | grep inet   # preferred — explicit interface
ip route | grep wlan | awk '{print $9}'
```

Expect `192.168.x.x`. Anything else is a problem (see below).

**Mobile-data-only diagnosis:** if the only non-loopback interface is `rmnet_data*` with an IP like `100.64.x.x – 100.127.x.x`, the phone is on mobile data with CGNAT. That IP is carrier-internal and NOT reachable from outside the phone — an MCP client on another device cannot connect to it directly. `ip route | grep wlan` will return nothing; use `ip -4 addr` or `ifconfig` to confirm.

**Tunneling from Termux on mobile data — pick by what actually connects:**

**First try: Cloudflare Quick Tunnel (best when it works)**

```bash
~/bin/cloudflared tunnel --url http://localhost:8081 --no-autoupdate
```

Output line to copy:
```
Your quick tunnel has been created: https://<random-words>.trycloudflare.com/mcp
```

The tunnel process must keep running for the URL to stay live; Termux kills it on force-stop, so keep the terminal session alive or background it.

**CF tunnel often fails on Termux mobile data** with `dial tcp: lookup api.trycloudflare.com on [::1]:53: read udp ...: connection refused`. That is Termux's glibc trying IPv6 first for `api.trycloudflare.com` and finding no working IPv6 DNS on the carrier. `sysctl -w net.ipv6.conf.all.disable_ipv6=1` is denied (no root), `GODEBUG=netdns=cgo` doesn't help, and editing `/etc/hosts` to pin the resolved IPv4 still loses to the IPv6 resolution path the Go binary walks first. Don't burn time on those workarounds.

**Second choice: localhost.run SSH tunnel — reliable on mobile data**

```bash
ssh -o StrictHostKeyChecking=no -R 80:localhost:8081 nokey@localhost.run
```

Output contains a URL line like:
```
<32-hex>.lhr.life tunneled with tls termination, https://<32-hex>.lhr.life
```

Use `https://<32-hex>.lhr.life/mcp` as the MCP URL. Free, no account, no key needed. Same rule: the SSH process must stay alive (background it in Termux; it dies on force-stop). The URL changes every run — write the fresh URL back to wherever the client expects it (e.g. a shared state file).

**Verify the tunnel actually carries MCP (not just HTTPS):**

```bash
curl -s -X POST https://<tunnel-host>/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

Expect `serverInfo.name = "termux-native-mcp"`. `curl -X POST` with no Accept header may return `405` or `Missing Mcp-Session-Id` — that's still alive, just needs the MCP-stream headers.

**Do not try to expose Termux MCP on a CGNAT mobile-data IP directly** — no port forwarding, no NAT tricks; the carrier won't accept inbound traffic on CGNAT ranges.

Upstream: https://github.com/termuxgpt/termux-mcp

## Claude Code CLI on Termux — NOT RUNNABLE

`@anthropic-ai/claude-code` published on npm does not ship a native binary for `linux-arm64-android` (Termux). Available targets: `darwin-arm64`, `darwin-x64`, `linux-x64`, `linux-arm64`, `linux-x64-musl`, `linux-arm64-musl`, `win32-x64`, `win32-arm64`. Termux is not in the list.

**Symptom:** after `npm install -g @anthropic-ai/claude-code`, running `claude` prints:

```
Error: claude native binary not installed.
Either postinstall did not run ...
```

and `node install.cjs` explicitly rejects with:

```
Native binaries for linux-arm64-android are not available on this release channel.
```

**Do not waste time trying**:
- Different npm versions / pre-releases
- `--ignore-scripts` + manual binary hunt (no android binary exists)
- Rosetta-style translation layers on ARM — the binary architecture target simply isn't published
- `npx @anthropic-ai/claude-code` — same install, same missing binary

**Workarounds that DO work:**

1. **Remote Claude over SSH from a PC** — if the user has a real Linux/macOS machine, run Claude Code there, SSH into Termux for terminal access. The MCP client is on the PC, Termux is the peer.
2. **Use another AI agent that runs on Android** — Hermes Agent (this agent), or a mobile-native AI that accepts custom MCP URLs. Point them at `http://<phone-ip>:8081/mcp`.
3. **Colab or PC for coding agents, Termux as shell peer** — code runs elsewhere, Termux MCP receives commands.

## Google Colab OAuth — Working Auth Flow in 2026

Colab's Python 3.13 environment has changed auth APIs. The methods that fail:

- `google.colab.auth.get_user_credentials(scopes=...)` — removed
- `google.colab.auth.user_credentials(scopes=...)` — removed
- `google.colab.auth.credentials(scopes=...)` — removed
- `google.colab.auth.authenticate_user(scopes=...)` — accepts no `scopes` arg
- `InstalledAppFlow.run_console()` — removed
- `InstalledAppFlow.run_local_server(port=0)` — fails with `Error: could not locate runnable browser` (Colab has no browser)
- `from google.auth import _credentials_mixin` — removed internal module

**What works:**

```python
from google.colab import auth

auth.authenticate_user()  # no scopes arg — signs in the Colab account
creds = auth._client.get_token()  # returns a token object; scope is whatever the Colab project was granted
```

**Limitation:** `authenticate_user()` signs in the Colab account with the scopes that Colab itself has been granted. If YouTube upload is not in that scope set, refreshing with extra scopes may not work, because the token object from `auth._client.get_token()` doesn't carry a user-configurable refresh flow. This is why "upload access" via Colab auth is unreliable — it depends on Colab's backend OAuth grant, not on your client ID/secret.

**Practical implication:** if the goal is YouTube upload from a mobile setup, do NOT rely on Colab-native auth. Either:

1. **Use the OAuth Client + redirect through a public tunnel** (Cloudflare Quick Tunnel / ngrok) so the redirect_uri matches the running server, not `localhost` (Google blocks localhost redirects from mobile since 2024).
2. **Use Device Authorization Flow** if the OAuth client supports it — no redirect URI needed, just a device code typed at a URL.
3. **Run OAuth on a desktop and copy the token file** to Termux. One-time cost, works indefinitely.

## Client-ID/Secret Hygiene

When generating scripts that run in Colab or other client-side environments, do NOT hardcode the OAuth client_secret — it can end up in notebook history, screenshots, or logs. Read it from an environment variable:

```python
import os
client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
```

Colab has `runtime.set_variable(...)` for one-shot secret injection; keep the secret out of the visible notebook cell content.
