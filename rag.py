"""
rag.py — local RAG over Dru's vault for DocBot (FastAPI backend).

No cloud. Embeddings via Ollama `nomic-embed-text`; index cached as a numpy
array + JSON metadata; retrieve() does cosine search and returns text with
`[source: <file>]` markers (the DocBot backend parses those for citations).

Runs in WSL (where Ollama + the venv live). OLLAMA_URL auto-falls back to the
Windows-host IP when localhost is refused (Ollama is a Windows app).
"""
import os
import json
import time
import hashlib
import subprocess
import urllib.request
import numpy as np

VAULT_PATH = os.getenv("VAULT_PATH",
                        "/mnt/c/Users/mwint/hermes_space/Hermes_vault")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
STORE_DIR = os.path.expanduser("~/docbot_rag_store")  # WSL-local (avoids /mnt/c mount perm issues)
INDEX = os.path.join(STORE_DIR, "index.npy")
META = os.path.join(STORE_DIR, "meta.json")

# Ollama runs as a Windows app; from WSL, localhost:11434 is refused.
# Use the confirmed Windows-host gateway IP (WSL default route), fall back to localhost.
OLLAMA_HOST = "172.24.128.1"   # Windows host gateway (verified reachable from WSL)
OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://{OLLAMA_HOST}:11434").rstrip("/")

CHUNK = 900
OVERLAP = 120
EXTS = (".md", ".txt")


def _sig(path):
    try:
        st = os.stat(path)
        return f"{st.st_size}:{int(st.st_mtime)}"
    except OSError:
        return "0:0"


def _embed(text):
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        OLLAMA_URL + "/api/embeddings",
        data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return np.array(json.load(r)["embedding"], dtype=np.float32)


def _chunk_text(text):
    text = text.replace("\r\n", "\n")
    if len(text) <= CHUNK:
        return [text] if text.strip() else []
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + CHUNK])
        i += CHUNK - OVERLAP
    return out


def _iter_files():
    for root, _dirs, files in os.walk(VAULT_PATH):
        # skip heavy/irrelevant dirs
        if any(s in root for s in ("/.git", "/node_modules", "/__pycache__",
                                   "/voiceagent_store", "/rag_store",
                                   "/chroma_store", "/.obsidian")):
            continue
        for f in files:
            if f.lower().endswith(EXTS):
                yield os.path.join(root, f)


def build_index(force=False):
    os.makedirs(STORE_DIR, exist_ok=True)
    sigs = {os.path.relpath(p, VAULT_PATH): _sig(p) for p in _iter_files()}
    if not force and os.path.exists(META) and os.path.exists(INDEX):
        try:
            old = json.load(open(META))["sigs"]
            if old == sigs:
                print(f"[rag] index fresh ({len(sigs)} files), skip")
                return
        except Exception:
            pass
    print(f"[rag] building index over {len(sigs)} files...")
    records, vecs = [], []
    for rel, sig in sigs.items():
        if sig == "0:0":
            continue
        try:
            text = open(os.path.join(VAULT_PATH, rel), encoding="utf-8",
                        errors="ignore").read()
        except OSError:
            continue
        for ci, ch in enumerate(_chunk_text(text)):
            try:
                v = _embed(ch)
            except Exception as e:
                print(f"[rag] embed failed for {rel}[{ci}]: {e}")
                continue
            vecs.append(v)
            records.append({"rel": rel, "chunk": ci, "text": ch})
    if not vecs:
        raise RuntimeError("no chunks embedded — Ollama reachable?")
    arr = np.stack(vecs).astype(np.float32)
    np.save(INDEX, arr)
    json.dump({"sigs": sigs, "records": records, "dim": arr.shape[1]},
              open(META, "w"), ensure_ascii=False)
    print(f"[rag] indexed {len(records)} chunks -> {STORE_DIR}")


def retrieve(query, k=4):
    if not (os.path.exists(INDEX) and os.path.exists(META)):
        build_index(force=True)
    arr = np.load(INDEX)
    meta = json.load(open(META))
    q = _embed(query)
    qn = q / (np.linalg.norm(q) + 1e-9)
    an = arr / (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9)
    sims = an @ qn
    top = np.argsort(-sims)[:k]
    lines = []
    for i in top:
        rec = meta["records"][int(i)]
        lines.append(f"[source: {rec['rel']}]\n{rec['text']}")
    return "\n\n".join(lines)


if __name__ == "__main__":
    t = time.time()
    build_index(force=True)
    print("sample retrieve:", "-" * 20)
    print(retrieve("what happens in The Park?", k=2)[:600])
    print(f"[rag] done in {time.time() - t:.1f}s")
