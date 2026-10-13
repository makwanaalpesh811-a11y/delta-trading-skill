#!/data/data/com.termux/files/usr/bin/bash
# Start/stop/status the Hermes + external-AI collaboration stack
# Wraps termux-native-mcp + localhost.run SSH tunnel on Termux (Android).
#
# Usage:
#   ~/start_collab.sh start      # start everything
#   ~/start_collab.sh status     # check both PIDs + POST initialize
#   ~/start_collab.sh stop       # kill both
#   ~/start_collab.sh restart    # stop + start

set -e

STATE_FILE=~/Hermes_Almari/99_COLLABORATION/state.json
LOG_DIR=~/Hermes_Almari/99_COLLABORATION/scripts/logs
mkdir -p "$LOG_DIR"

MCP_PID_FILE=~/collab_mcp.pid
TUNNEL_PID_FILE=~/collab_tunnel.pid
MCP_PORT=8081

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok() { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
info() { echo -e "${YELLOW}[..]${NC} $1"; }

pid_alive() { [[ -f "$1" ]] && kill -0 "$(cat "$1")" 2>/dev/null; }

start_mcp() {
    if pid_alive "$MCP_PID_FILE"; then
        info "MCP already running (PID $(cat "$MCP_PID_FILE"))"; return 0
    fi
    info "Starting termux-native-mcp on port ${MCP_PORT}..."
    nohup termux-native-mcp --port "$MCP_PORT" > "$LOG_DIR/mcp.log" 2>&1 &
    echo $! > "$MCP_PID_FILE"
    sleep 2
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${MCP_PORT}/mcp" 2>/dev/null || echo 000)
    # 405 = alive but wrong method, 200 = alive with proper POST, both OK
    if [[ "$code" == "405" || "$code" == "200" ]]; then
        ok "MCP server running (PID $(cat "$MCP_PID_FILE"))"
    else
        fail "MCP failed to start — check $LOG_DIR/mcp.log"
    fi
}

start_tunnel() {
    if pid_alive "$TUNNEL_PID_FILE"; then
        info "Tunnel already running (PID $(cat "$TUNNEL_PID_FILE"))"; return 0
    fi
    info "Starting localhost.run tunnel..."
    (
        exec ssh -o StrictHostKeyChecking=no \
               -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
               -R 80:localhost:${MCP_PORT} nokey@localhost.run
    ) > "$LOG_DIR/tunnel.log" 2>&1 < /dev/null &
    echo $! > "$TUNNEL_PID_FILE"

    local url=""
    for _ in $(seq 1 30); do
        sleep 1
        url=$(grep -oE 'https://[a-f0-9]{12,32}\.lhr\.life' "$LOG_DIR/tunnel.log" 2>/dev/null | head -1 || true)
        [[ -n "$url" ]] && break
    done
    if [[ -z "$url" ]]; then
        fail "Tunnel didn't respond in 30s — check $LOG_DIR/tunnel.log"
        return 1
    fi
    ok "Tunnel running (PID $(cat "$TUNNEL_PID_FILE"))"
    echo "    MCP URL: ${url}/mcp"

    # Update state.json with the fresh URL (URL changes every run)
    python3 - <<PYEOF
import json
p = '$STATE_FILE'
d = json.load(open(p))
d['tunnel_url'] = '$url'
d['manus_mcp_url'] = '$url/mcp'
d['tunnel_pid'] = $(cat "$TUNNEL_PID_FILE")
d['mcp_pid'] = $(cat "$MCP_PID_FILE")
d['last_updated'] = '$(date '+%Y-%m-%d %H:%M IST')'
json.dump(d, open(p,'w'), indent=2, ensure_ascii=False)
PYEOF
    echo "- $(date '+%H:%M') — Tunnel started: ${url}/mcp" >> ~/Hermes_Almari/99_COLLABORATION/journal/$(date +%Y-%m-%d).md
}

check_status() {
    echo ""; echo "========== COLLAB STATUS =========="; echo ""

    if pid_alive "$MCP_PID_FILE"; then
        ok "MCP server:  RUNNING (PID $(cat "$MCP_PID_FILE"), port ${MCP_PORT})"
    else
        fail "MCP server:  STOPPED"
    fi

    if pid_alive "$TUNNEL_PID_FILE"; then
        ok "Tunnel:      RUNNING (PID $(cat "$TUNNEL_PID_FILE"))"
    else
        fail "Tunnel:      STOPPED"
    fi

    local url
    url=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('manus_mcp_url',''))" 2>/dev/null || echo "")
    if [[ -n "$url" ]]; then
        echo "    URL:       ${url}"
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$url" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json, text/event-stream" \
            -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' 2>/dev/null || echo 000)
        if [[ "$code" == "200" ]]; then
            ok "Public test: HTTP 200 (MCP responding)"
        else
            fail "Public test: HTTP $code (tunnel or MCP down)"
        fi
    fi

    echo ""; echo "========== FILES =========="
    echo "State:   $STATE_FILE"
    echo "Prompt:  ~/Hermes_Almari/99_COLLABORATION/manus_master_prompt.txt"
    echo "Tasks:   ~/Hermes_Almari/99_COLLABORATION/pending/tasks.md"
    echo "Logs:    $LOG_DIR/"
}

stop_all() {
    if pid_alive "$TUNNEL_PID_FILE"; then
        kill "$(cat "$TUNNEL_PID_FILE")" 2>/dev/null && ok "Tunnel stopped" || info "Tunnel PID stale"
        rm -f "$TUNNEL_PID_FILE"
    fi
    if pid_alive "$MCP_PID_FILE"; then
        kill "$(cat "$MCP_PID_FILE")" 2>/dev/null && ok "MCP stopped" || info "MCP PID stale"
        rm -f "$MCP_PID_FILE"
    fi
    pkill -f "termux-native-mcp" 2>/dev/null || true
    pkill -f "nokey@localhost.run" 2>/dev/null || true
}

case "${1:-start}" in
    start)   start_mcp; start_tunnel; check_status ;;
    status)  check_status ;;
    stop)    stop_all ;;
    restart) stop_all; sleep 2; start_mcp; start_tunnel ;;
    *) echo "Usage: $0 {start|stop|status|restart}"; exit 1 ;;
esac
