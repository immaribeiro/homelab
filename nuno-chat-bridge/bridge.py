#!/usr/bin/env python3
"""nuno-chat-bridge — thin authenticated relay between nuno.immas.org and the
Hermes API server (the gateway's OpenAI-compatible endpoint).

Flow:  browser → site nginx (/api/) → this bridge (:8643) → Hermes API server
(:8642, 127.0.0.1) → agent session "nuno-site" (full tools + memory).

Security model:
  - The Hermes API key NEVER leaves this machine. The site only holds a weak
    SITE_TOKEN (public by design — the site is client-side); this process
    holds the real key and validates the token with a constant-time compare.
  - Rate limiting: per-IP sliding window (default 20/hour) + global daily cap.
  - Message length capped at 2000 chars. No shell, no HTML — plain text to the
    LLM only.

Config: ~/.hermes/env/nuno-chat-bridge.env (chmod 600), loaded at startup.
Logs:   ~/.hermes/logs/nuno-chat-bridge.log
"""
import hmac
import json
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

HOME = Path.home()
ENV_FILE = HOME / ".hermes/env/nuno-chat-bridge.env"
LOG_FILE = HOME / ".hermes/logs/nuno-chat-bridge.log"


def load_env(path: Path) -> dict:
    env = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


env = load_env(ENV_FILE)
API_URL = env.get("HERMES_API_URL", "http://127.0.0.1:8642").rstrip("/")
API_KEY = env.get("HERMES_API_KEY", "")
SITE_TOKEN = env.get("SITE_TOKEN", "")
CONVERSATION = env.get("CHAT_CONVERSATION", "nuno-site")
RATE_PER_IP = int(env.get("RATE_LIMIT_PER_IP", "20"))
RATE_WINDOW = 3600.0
GLOBAL_DAILY_CAP = 300
MAX_MESSAGE = 2000

SYSTEM_PROMPT = (
    "Tu és a Hermes, a assistente pessoal de IA da Imma e do Nuno, integrada no site "
    "nuno.immas.org (que manténs: eventos, notícias, página Us, pipeline diário 06:00). "
    "O Nuno fala contigo a partir do site. Responde sempre em português de Portugal, "
    "com tom caloroso, direto e conciso. Podes usar as tuas ferramentas, memória e skills "
    "para responder e para agir: acrescentar tópicos de notícias, ajustar couple.json, "
    "recomendar eventos, propor mudanças no site. Se um pedido exigir alterações de código, "
    "explica o que vais fazer antes de o descreveres como feito."
)

app = FastAPI(title="nuno-chat-bridge")
_hits = defaultdict(deque)
_hits_lock = Lock()
_global_hits = deque()
_start = time.time()


def _log(line: str) -> None:
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {line}\n")
    except OSError:
        pass


def _rate_limited(client_ip: str) -> bool:
    now = time.time()
    with _hits_lock:
        bucket = _hits[client_ip]
        while bucket and now - bucket[0] > RATE_WINDOW:
            bucket.popleft()
        if len(bucket) >= RATE_PER_IP:
            return True
        bucket.append(now)
        while _global_hits and now - _global_hits[0] > 86400:
            _global_hits.popleft()
        if len(_global_hits) >= GLOBAL_DAILY_CAP:
            return True
        _global_hits.append(now)
    return False


def _extract_reply(data: dict) -> str:
    reply = data.get("output_text") or ""
    if not reply:
        parts = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for chunk in item.get("content", []):
                    if chunk.get("type") == "output_text":
                        parts.append(chunk.get("text", ""))
        reply = "\n".join(parts).strip()
    return reply


@app.get("/health")
def health():
    return {"status": "ok", "service": "nuno-chat-bridge", "uptime": int(time.time() - _start)}


@app.post("/api/chat")
async def chat(request: Request, authorization: str = Header(default="")):
    t0 = time.time()
    client_ip = request.headers.get("X-Real-IP") or (
        request.client.host if request.client else "?"
    )
    _log(f"POST /api/chat from {client_ip}")

    token = authorization.removeprefix("Bearer ").strip()
    if not SITE_TOKEN or not hmac.compare_digest(token, SITE_TOKEN):
        _log("401 unauthorized")
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    if _rate_limited(client_ip):
        _log("429 rate limited")
        return JSONResponse(
            {"error": "Demasiados pedidos — tenta outra vez daqui a pouco."},
            status_code=429,
        )
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    message = str(body.get("message") or "").strip()
    if not message or len(message) > MAX_MESSAGE:
        return JSONResponse({"error": "mensagem vazia ou demasiado longa"}, status_code=400)

    payload = {
        "input": message,
        "conversation": CONVERSATION,
        "instructions": SYSTEM_PROMPT,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=160.0) as client:
            resp = await client.post(f"{API_URL}/v1/responses", headers=headers, json=payload)
            if resp.status_code in (404, 400) and "conversation" in resp.text:
                # Fallback: stateless chat completions (single turn).
                resp = await client.post(
                    f"{API_URL}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": "hermes-agent",
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": message},
                        ],
                        "stream": False,
                    },
                )
    except Exception as exc:
        _log(f"upstream error: {exc!r}")
        return JSONResponse(
            {"error": "A Hermes está offline — tenta outra vez num minuto."},
            status_code=503,
        )

    if resp.status_code != 200:
        _log(f"upstream status {resp.status_code}: {resp.text[:300]}")
        return JSONResponse(
            {"error": "A Hermes teve um problema — tenta outra vez."}, status_code=502
        )
    try:
        data = resp.json()
    except Exception:
        _log("upstream returned non-JSON")
        return JSONResponse({"error": "A Hermes teve um problema — tenta outra vez."}, status_code=502)

    if resp.url.path.endswith("/chat/completions"):
        reply = (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
    else:
        reply = _extract_reply(data)
    reply = reply or "(sem resposta)"
    _log(f"replied in {time.time() - t0:.1f}s ({len(reply)} chars)")
    return {"reply": reply, "conversation": CONVERSATION, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8643, log_level="warning")
