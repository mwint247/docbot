"""
docbot_backend.py — FastAPI backend for the DocBot website.

Endpoints:
  POST /api/chat   {query, history?} -> {answer, sources}
  POST /api/tts    {text}            -> audio/wav (Piper)
  GET  /           serves the frontend HTML

Runs in WSL (where Ollama + piper + the venv live). Browser reaches it via
WSL2 localhost forwarding (same as the VoiceAgent console).

Env: OLLAMA_URL, OLLAMA_MODEL (LLM), EMBED_MODEL, PIPER_VOICE, PIPER_MODEL_DIR.
"""
import os, json, urllib.request, io, wave
from fastapi import FastAPI, Request
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware

import rag

OLLAMA_URL = rag.OLLAMA_URL
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "hermes3:8b")
PIPER_VOICE = os.getenv("PIPER_VOICE", "en_US-lessac-medium")
PIPER_MODEL_DIR = os.getenv("PIPER_MODEL_DIR",
    os.path.expanduser("~/docbot_piper_voices"))  # WSL-local (avoids /mnt/c perm issues)

# Build the index on startup if missing.
try:
    if not (os.path.exists(rag.INDEX) and os.path.exists(rag.META)):
        print("[docbot] building index...")
        rag.build_index(force=True)
    else:
        print("[docbot] index present")
except Exception as e:
    print("[docbot] index build note:", e)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                  allow_headers=["*"])

HTML = os.path.join(os.path.dirname(__file__), "docbot_frontend.html")

@app.get("/")
def index():
    return FileResponse(HTML)

def _ollama_chat(system, user):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "stream": False,
    }
    req = urllib.request.Request(
        OLLAMA_URL + "/v1/chat/completions",  # OpenAI-compatible
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"]

@app.post("/api/chat")
async def chat(req: Request):
    body = await req.json()
    query = (body.get("query") or "").strip()
    history = body.get("history") or []
    if not query:
        return Response(json.dumps({"error": "empty query"}),
                        media_type="application/json", status_code=400)
    context = rag.retrieve(query, k=4)
    system = (
        "You are DocBot, a technical assistant for Drew Gilbert. Answer using ONLY "
        "the retrieved documentation excerpts below. If the excerpts don't cover it, "
        "say so plainly. Cite the source file names. Be concise and practical — "
        "focus on resolving the technical issue. Keep spoken-style replies under 60 words."
    )
    user_msg = f"Retrieved docs:\n{context}\n\nQuestion: {query}"
    answer = _ollama_chat(system, user_msg)
    # extract source filenames from the context for display
    sources = []
    for line in context.splitlines():
        if line.startswith("[source:"):
            sources.append(line[len("[source:"):-1].strip())
    return Response(json.dumps({"answer": answer, "sources": sources[:4]}),
                    media_type="application/json")

@app.post("/api/tts")
async def tts(req: Request):
    body = await req.json()
    text = (body.get("text") or "").strip()
    if not text:
        return Response(b"", media_type="audio/wav", status_code=400)
    from piper import PiperVoice
    onnx = os.path.join(PIPER_MODEL_DIR, f"{PIPER_VOICE}.onnx")
    voice = PiperVoice.load(onnx)
    pcm = b"".join(c.audio_int16_bytes for c in voice.synthesize(text))
    # Piper yields raw 16-bit PCM; browsers need a real WAV container.
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(voice.config.sample_rate)
        wf.writeframes(pcm)
    return Response(buf.getvalue(), media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8123)
