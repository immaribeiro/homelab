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
import asyncio
import hmac
import json
import re
import subprocess
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock, Thread

import httpx
from fastapi import FastAPI, File, Header, Request, UploadFile
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

# Photo upload: saved to the site repo's src_photos/, converted via pipeline.py
# (which also writes the live public/photos/manifest.json), then committed +
# pushed in a background thread. The pod serves photos live from a mounted
# hostPath volume, so the upload response never waits on git or CI.
NUNO_SITE_DIR = HOME / "GitHub/nuno-site"
SRC_PHOTOS_DIR = NUNO_SITE_DIR / "src_photos"
NUNO_SITE_PYTHON = NUNO_SITE_DIR / ".venv" / "bin" / "python"
ALLOWED_UPLOAD_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024

SYSTEM_PROMPT = (
    "Tu és a Hermes, a assistente pessoal de IA da Imma e do Nuno, integrada no site "
    "nuno.immas.org (que manténs: eventos, notícias, página Us, pipeline diário 06:00). "
    "O Nuno fala contigo a partir do site. "
    "IMPORTANTE — quem são: o Imma é um HOMEM (pronomes masculinos: «ele», «o Imma»), "
    "o Nuno é um homem, e os dois formam um casal homossexual. O Imma NÃO é uma mulher: "
    "nunca te refiras a ele com pronomes ou artigos femininos («ela», «a Imma»), e nunca "
    "descrevas a relação como heterossexual. Usa sempre o masculino ao falar do Imma. "
    "Responde sempre em português de Portugal, "
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

# Serializes photo uploads: pipeline.py recomputes the full manifest by scanning
# src_photos, so two near-simultaneous uploads could drop an entry otherwise.
_upload_lock = Lock()


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


def _upload_auth_and_ratelimit(client_ip: str, authorization: str) -> tuple[bool, JSONResponse | None]:
    """Shared gate for uploads/refresh: token check + per-IP rate limit."""
    token = authorization.removeprefix("Bearer ").strip()
    if not SITE_TOKEN or not hmac.compare_digest(token, SITE_TOKEN):
        _log("upload 401 unauthorized")
        return False, JSONResponse({"error": "unauthorized"}, status_code=401)
    if _rate_limited(client_ip or "?"):
        _log("upload 429 rate limited")
        return False, JSONResponse(
            {"error": "Demasiados pedidos — tenta outra vez daqui a pouco."},
            status_code=429,
        )
    return True, None


def _slug_for(stem: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or "photo"


def _commit_and_push(unique: str) -> None:
    """Commit + push new photos in the background; failures only get logged."""
    try:
        subprocess.run(
            ["git", "add", "public/photos", "public/manifest.json"],
            cwd=str(NUNO_SITE_DIR), check=True, capture_output=True, text=True,
        )
        # Only commit when the pipeline actually changed something.
        changed = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "public/photos", "public/manifest.json"],
            cwd=str(NUNO_SITE_DIR), capture_output=True, text=True,
        )
        if changed.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m", f"site photos: add {unique}"],
                cwd=str(NUNO_SITE_DIR), check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=str(NUNO_SITE_DIR), check=True, capture_output=True, text=True, timeout=60,
            )
        _log(f"upload git ok {unique}")
    except Exception as exc:
        _log(f"upload git background failed for {unique}: {exc!r}")


# Serializes manual data refreshes: fetch_events.py / fetch_news.py rewrite the
# live JSON files, so two near-simultaneous refreshes could interleave.
_refresh_lock = Lock()


def _run_fetchers() -> dict:
    """Run fetch_events.py + fetch_news.py on the host (writes public/*.json).

    The pod serves those files live from the mounted hostPath volume, so this
    is all that's needed for the site to show fresh data — no git, no CI, no
    rollout. Returns a summary dict for the API response.
    """
    py = "/usr/bin/python3"
    summary = {"events": None, "news": None, "errors": []}
    try:
        events = subprocess.run(
            [py, "fetch_events.py", "--days", "14"],
            cwd=str(NUNO_SITE_DIR), capture_output=True, text=True, timeout=180,
        )
        if events.returncode != 0:
            summary["errors"].append(f"fetch_events: {events.stderr[-300:]}")
        else:
            last = [ln for ln in events.stdout.strip().splitlines() if ln][-1] if events.stdout.strip() else ""
            summary["events"] = last
            _log(f"refresh events ok: {last}")
    except Exception as exc:
        summary["errors"].append(f"fetch_events: {exc!r}")
    try:
        news = subprocess.run(
            [py, "fetch_news.py"],
            cwd=str(NUNO_SITE_DIR), capture_output=True, text=True, timeout=180,
        )
        if news.returncode != 0:
            summary["errors"].append(f"fetch_news: {news.stderr[-300:]}")
        else:
            last = [ln for ln in news.stdout.strip().splitlines() if ln][-1] if news.stdout.strip() else ""
            summary["news"] = last
            _log(f"refresh news ok: {last}")
    except Exception as exc:
        summary["errors"].append(f"fetch_news: {exc!r}")
    return summary


@app.post("/api/refresh")
async def refresh_data(
    request: Request,
    authorization: str = Header(default=""),
):
    """Manual 'update now' for the site's events + news (no rebuild needed).

    Reuses the same token gate + rate limit as uploads. The fetchers write the
    live JSON files on the host; the pod picks them up instantly via the
    mounted hostPath volume.
    """
    ok, err = _upload_auth_and_ratelimit(
        request.headers.get("X-Real-IP") or (request.client.host if request.client else ""),
        authorization,
    )
    if not ok:
        return err
    await asyncio.to_thread(_refresh_lock.acquire)
    try:
        summary = await asyncio.to_thread(_run_fetchers)
    finally:
        _refresh_lock.release()
    if summary["errors"]:
        _log(f"refresh partial errors: {summary['errors']}")
        return JSONResponse({"ok": False, "errors": summary["errors"]}, status_code=502)
    # Git backup in the background — CI ignores these files, so no rebuild.
    Thread(target=_commit_and_push, args=("data-refresh",), daemon=True).start()
    return {"ok": True, "events": summary["events"], "news": summary["news"]}


@app.post("/api/upload")
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
):
    """Receive a photo from the site, optimize it, and publish it live."""
    ok, err = _upload_auth_and_ratelimit(
        request.headers.get("X-Real-IP") or (request.client.host if request.client else ""),
        authorization,
    )
    if not ok:
        return err

    filename = (file.filename or "photo.jpg").lower()
    ext = Path(filename).suffix
    if ext not in ALLOWED_UPLOAD_EXT:
        _log(f"upload 400 bad extension {ext}")
        return JSONResponse(
            {"error": "Formato não suportado — usa JPG, PNG, WebP ou HEIC."}, status_code=400
        )

    data = await file.read()
    if not data or len(data) > MAX_UPLOAD_BYTES:
        _log(f"upload 413 too large ({len(data)} bytes)")
        return JSONResponse(
            {"error": "Ficheiro demasiado grande (máx. 15 MB)."}, status_code=413
        )

    if not SRC_PHOTOS_DIR.exists():
        _log("upload 503 nuno-site repo missing")
        return JSONResponse({"error": "Repositório indisponível — tenta mais tarde."}, status_code=503)

    stem = Path(filename).stem
    unique = f"upload-{time.strftime('%Y%m%d-%H%M%S')}-{_slug_for(stem)}{ext}"
    dest = SRC_PHOTOS_DIR / unique

    # The pipeline recomputes the full manifest by scanning src_photos, so two
    # near-simultaneous uploads could produce a manifest that drops an entry.
    # Hold the upload lock across the whole write + pipeline critical section.
    await asyncio.to_thread(_upload_lock.acquire)
    try:
        try:
            dest.write_bytes(data)
        except OSError as exc:
            _log(f"upload 500 write failed: {exc!r}")
            return JSONResponse({"error": "Não foi possível guardar a foto."}, status_code=500)

        # Optimize + regenerate manifest via the site's own pipeline (uses its venv).
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                [str(NUNO_SITE_PYTHON), "pipeline.py"],
                cwd=str(NUNO_SITE_DIR),
                capture_output=True,
                text=True,
                timeout=180,
            )
        except Exception as exc:
            _log(f"upload 500 pipeline run failed: {exc!r}")
            return JSONResponse({"error": "Pipeline de imagem falhou."}, status_code=500)
        if proc.returncode != 0:
            _log(f"upload 500 pipeline exit {proc.returncode}: {proc.stderr[-300:]}")
            return JSONResponse({"error": "Processamento da imagem falhou."}, status_code=500)
    finally:
        _upload_lock.release()

    # Git commit + push runs in a background daemon thread: the photo is served
    # live from the mounted volume, so the upload response never waits on git.
    Thread(target=_commit_and_push, args=(unique,), daemon=True).start()

    webp_name = f"{Path(unique).stem}.webp"
    _log(f"upload ok {unique} -> {webp_name}")
    return {
        "ok": True,
        "src": f"/photos/{webp_name}",
        "message": "Foto enviada! A foto aparece já.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8643, log_level="warning")
