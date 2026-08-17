# DocBot

A local, private RAG assistant that answers questions over Drew Gilbert's
documentation vault using Ollama (LLM + embeddings) and Piper (TTS). No cloud —
everything runs on the local machine / WSL2.

**Created by Drew Gilbert**

## What it does

- Ingests the Obsidian vault (`.md`/`.txt`) into a local cosine-similarity
  index (numpy + JSON metadata, cached to `~/docbot_rag_store`).
- Serves a FastAPI backend (`docbot_backend.py`) with:
  - `POST /api/chat` — RAG answer with source citations
  - `POST /api/tts`  — Piper-synthesized WAV voice
  - `GET  /`        — the single-file frontend (`docbot_frontend.html`)
- Frontend is a self-contained HTML page with a chat + TTS UI.

## Architecture

```
docbot_frontend.html   -- browser UI (chat + speak)
docbot_backend.py      -- FastAPI: chat + tts endpoints, serves the HTML
rag.py                 -- local RAG: chunk -> embed (nomic-embed-text) -> cosine retrieve
```

## Setup

1. Ollama running with `hermes3:8b` and `nomic-embed-text`.
2. Piper voice model under `~/docbot_piper_voices` (or set `PIPER_MODEL_DIR`).
3. Env vars (all optional, sensible defaults in code):
   - `OLLAMA_URL` / `OLLAMA_MODEL` — LLM endpoint + model
   - `EMBED_MODEL` — embedding model
   - `VAULT_PATH` — path to the docs vault
   - `PIPER_VOICE` / `PIPER_MODEL_DIR` — TTS
4. Launch: `bash start_docbot.sh` (or run `docbot_backend.py` with uvicorn on :8123).

## Notes

Runs in WSL2; Ollama is a Windows app reached via the host gateway IP
(`172.24.128.1` by default). The index is rebuilt automatically on startup
if the vault signature changes.
