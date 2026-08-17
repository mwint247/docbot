#!/usr/bin/env bash
# restart_docbot.sh — kill any running DocBot backend, then relaunch detached.
# Run from inside a WSL terminal:
#   cd /mnt/c/Users/mwint/hermes_space/Hermes_vault/ai_projects/DocBot
#   bash restart_docbot.sh
set -u

DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. stop any existing instance
if pgrep -f "uvicorn docbot_backend" >/dev/null 2>&1; then
  echo "[docbot] stopping existing instance..."
  pkill -f "uvicorn docbot_backend"
  sleep 2
else
  echo "[docbot] no running instance found"
fi

# 2. relaunch detached so it survives the terminal closing
cd "$DIR"
export PATH="$HOME/.local/bin:$PATH"
setsid bash start_docbot.sh > /tmp/docbot.log 2>&1 < /dev/null &

echo "[docbot] relaunched (pid $!) — logs: tail -f /tmp/docbot.log"
echo "[docbot] UI: http://localhost:8123  (wait ~7s, or longer on first index build)"
