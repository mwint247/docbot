#!/usr/bin/env bash
# start_docbot.sh — launch the DocBot FastAPI backend in WSL (no Docker).
# Requires: ~/docbot_venv with fastapi, uvicorn, piper-tts, numpy,
#           plus OLLAMA_URL/OLLAMA_MODEL in env (loaded from VoiceAgent/.env or export).
set -e
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
if [ -f ~/docbot_venv/bin/activate ]; then
  . ~/docbot_venv/bin/activate
else
  echo "[docbot] ERROR: ~/docbot_venv not found. Create it: python3.14 -m venv ~/docbot_venv && . ~/docbot_venv/bin/activate && pip install fastapi uvicorn piper-tts numpy"
  exit 1
fi
# pull Ollama/piper settings from the VoiceAgent .env if present
if [ -f ../VoiceAgent/.env ]; then
  set -a; . ../VoiceAgent/.env; set +a
fi
# Ollama is a Windows app. From WSL, localhost:11434 is REFUSED, but the
# Windows-host gateway IP works. The VoiceAgent .env sets OLLAMA_URL=localhost
# (correct for the Node agent on the Windows host), so force the WSL-correct
# host here, otherwise every Ollama call fails with a connection error.
export OLLAMA_URL="http://172.24.128.1:11434"
export EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"
export PIPER_MODEL_DIR="${PIPER_MODEL_DIR:-$HOME/docbot_piper_voices}"
echo "[docbot] starting on :8123 (WSL localhost forwarding -> Windows browser)"
exec uvicorn docbot_backend:app --host 0.0.0.0 --port 8123
