@echo off
REM DocBot launcher - boots WSL, starts the DocBot FastAPI backend (persistent),
REM waits, then opens the web UI.
REM
REM FIX (was hanging): old version ran
REM   wsl -d Ubuntu -e bash -c "... start_docbot.sh &"
REM The trailing '&' backgrounded the server INSIDE the bash wrapper, but WSL2
REM kills every child of a wsl invocation the moment that wsl call returns.
REM So the server died before the wait-loop saw it -> 60s timeout -> pause.
REM FIX: use `start` so wsl is its own persistent process, and `exec` so the
REM server IS that wsl session (not a reaped child). Now it survives.
SETLOCAL
SET DOCBOTDIR=/mnt/c/Users/mwint/hermes_space/Hermes_vault/ai_projects/DocBot

echo [DocBot] Ensuring WSL is up...
wsl -d Ubuntu -e true >nul 2>&1

echo [DocBot] Starting backend in WSL (first launch builds the vault index - may take a minute)...
REM `start` keeps wsl alive as its own process; `exec` makes uvicorn the session.
start "" wsl -d Ubuntu -e bash -c "export PATH=$HOME/.local/bin:$PATH; . ~/docbot_venv/bin/activate; cd %DOCBOTDIR%; exec bash start_docbot.sh > /tmp/docbot.log 2>&1"

echo [DocBot] Waiting for DocBot on :8123 ...
SET /A tries=0
:wait
curl -s -o nul -w "%%{http_code}" --max-time 3 http://localhost:8123/ 2>nul | findstr /r "^200$" >nul
IF %ERRORLEVEL%==0 GOTO up
SET /A tries+=1
IF %tries% GEQ 60 (
  echo [DocBot] ERROR: DocBot did not come up in 60s. Check: 'wsl -d Ubuntu -e bash -c "tail -20 /tmp/docbot.log"'
  pause
  EXIT /B 1
)
ping -n 2 127.0.0.1 >nul
GOTO wait

:up
echo [DocBot] DocBot is up. Opening web UI...
start "" "http://localhost:8123"
echo [DocBot] Done. Chat with it in the browser (RAG over your vault + TTS).
ENDLOCAL
