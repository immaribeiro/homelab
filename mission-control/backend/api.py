"""Hermes Mission Control — FastAPI application.

Read-only observability over all Hermes profiles. Default bind: 127.0.0.1.
See README for remote access guidance (Tailscale only).
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .aggregate import Store
from .auth import (_is_loopback, auth_enabled, hash_token,
                   load_or_create_token, token_matches)
from .db import default_hermes_home, discover_state_dbs, load_thread_profile_map
from .models import SessionStatus
from .stream import event_stream, POLL_SECONDS

APP_NAME = "Hermes Mission Control"
COOKIE_NAME = "mc_session"

HERMES_HOME = default_hermes_home()
DATA_DIR = Path(os.environ.get("MISSION_CONTROL_DATA_DIR", HERMES_HOME / "mission-control"))
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

BIND_HOST = os.environ.get("MISSION_CONTROL_HOST", "127.0.0.1")
BIND_PORT = int(os.environ.get("MISSION_CONTROL_PORT", "9118"))

# ── state ───────────────────────────────────────────────────────────────
store: Optional[Store] = None
token: str = ""
auth_on: bool = False
thread_map: dict = {}
dbs: List = []
_sse_conns = 0
MAX_SSE_CONNS = 8


def get_store() -> Store:
    if store is None:
        raise HTTPException(503, "store not initialised")
    return store


# ── auth ────────────────────────────────────────────────────────────────
def _cookie_valid(request: Request) -> bool:
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return False
    # The cookie holds a hash of the token (never the raw token), so a leaked
    # cookie cannot be replayed as a bearer credential, and rotating the token
    # invalidates all existing sessions.
    return token_matches(cookie, f"mc::{hash_token(token)}")


async def require_auth(request: Request,
                       x_auth_token: Optional[str] = Header(default=None)) -> None:
    if not auth_on:
        return
    if _cookie_valid(request):
        return
    if x_auth_token and token_matches(x_auth_token, token):
        return
    raise HTTPException(401, "authentication required")


# ── app ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global store, token, auth_on, thread_map, dbs
    loopback = _is_loopback(BIND_HOST)
    token = load_or_create_token(DATA_DIR, force=not loopback)
    auth_on = auth_enabled(BIND_HOST, token)
    dbs = discover_state_dbs()
    thread_map = load_thread_profile_map()
    store = Store(dbs, thread_map=thread_map)
    store.refresh()
    mode = "auth on (token required)" if auth_on else "open (loopback bind, no token)"
    print(f"[mission-control] {APP_NAME} v{__version__} | {len(dbs)} db(s) | {mode}")
    yield


app = FastAPI(title=APP_NAME, version=__version__, lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """CSP + hardening headers. The API serves private conversation data."""
    response = await call_next(request)
    path = request.url.path
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if path.startswith("/api/"):
        # Sensitive data: never cache.
        response.headers.setdefault("Cache-Control", "no-store")
    if not path.startswith("/api/"):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; form-action 'self'",
        )
    return response


@app.head("/api/health")
@app.get("/api/health")
def health():
    # Public readiness probe: minimal, no deployment metadata.
    return {"ok": True}


@app.post("/api/login")
async def login(request: Request, response: Response):
    body = await request.json()
    provided = (body or {}).get("token", "")
    if not auth_on:
        return {"ok": True}
    # CSRF hardening: same-origin POSTs only. Missing Origin (curl/CLI) is fine.
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    if origin:
        from urllib.parse import urlparse
        host = urlparse(origin).netloc
        allowed = {f"127.0.0.1:{BIND_PORT}", f"localhost:{BIND_PORT}",
                   BIND_HOST if ":" in BIND_HOST else f"{BIND_HOST}:{BIND_PORT}"}
        if host not in allowed:
            raise HTTPException(403, "cross-origin login rejected")
    if not token_matches(provided, token):
        raise HTTPException(401, "invalid token")
    # Bind the session to the token's hash (never the raw token).
    # Secure flag only over HTTPS (tailscale serve / reverse proxy): browsers
    # drop Secure cookies on plain HTTP, which would lock users out.
    secure = request.url.scheme == "https"
    response.set_cookie(COOKIE_NAME, f"mc::{hash_token(token)}", httponly=True,
                        samesite="strict", secure=secure, max_age=7 * 86400)
    return {"ok": True}


@app.get("/api/config")
def public_config():
    # Public surface stays minimal: the UI only needs to know whether to show
    # the login screen. Everything else lives behind auth (/api/info).
    return {"app": APP_NAME, "auth": auth_on}


@app.get("/api/info", dependencies=[Depends(require_auth)])
def info():
    return {
        "app": APP_NAME,
        "version": __version__,
        "auth": auth_on,
        "poll_seconds": POLL_SECONDS,
        "profiles": [p for p, _ in dbs],
        "hermes_home": str(HERMES_HOME),
    }


@app.get("/api/overview", dependencies=[Depends(require_auth)])
def overview():
    return get_store().overview()


@app.get("/api/sessions", dependencies=[Depends(require_auth)])
def sessions(
    agent: Optional[str] = None,
    profile: Optional[str] = None,
    source: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    date_from: Optional[float] = None,
    date_to: Optional[float] = None,
    active: Optional[bool] = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    st = get_store()
    rows = st.sessions
    if agent:
        rows = [s for s in rows if s.agent.lower() == agent.lower()]
    if profile:
        rows = [s for s in rows if (s.profile or "").lower() == profile.lower()]
    if source:
        rows = [s for s in rows if s.source.lower() == source.lower()]
    if model:
        rows = [s for s in rows if model.lower() in (s.model or "").lower()]
    if status:
        rows = [s for s in rows if s.status.value == status.lower()]
    if q:
        ql = q.lower()
        rows = [s for s in rows if ql in (s.title or "").lower()
                or ql in s.id.lower() or ql in (s.model or "").lower()
                or ql in s.source.lower()]
    if date_from is not None:
        rows = [s for s in rows if (s.started_at or 0) >= date_from]
    if date_to is not None:
        rows = [s for s in rows if (s.started_at or 0) <= date_to]
    if active is not None:
        rows = [s for s in rows if (s.ended_at is None) == active]

    total = len(rows)
    rows.sort(key=lambda s: s.last_activity_at or s.started_at or 0, reverse=True)
    page = rows[offset:offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "sessions": [s.to_dict() for s in page],
    }


@app.get("/api/sessions/{session_id}", dependencies=[Depends(require_auth)])
def session_detail(session_id: str, include_messages: bool = True,
                   include_children: bool = True):
    st = get_store()
    pair = st.get(session_id)
    if not pair:
        raise HTTPException(404, "session not found")
    s, _ = pair
    detail = s.to_dict()
    if include_messages:
        detail["messages"] = [m.to_dict() for m in st.messages(session_id)]
    if include_children:
        detail["children"] = [c.to_dict() for c in st.children(session_id)]
    return detail


@app.get("/api/agents", dependencies=[Depends(require_auth)])
def agents():
    return {"agents": get_store().agents()}


@app.get("/api/sources", dependencies=[Depends(require_auth)])
def sources():
    return {"sources": get_store().sources()}


@app.get("/api/search", dependencies=[Depends(require_auth)])
def search(q: str = Query(..., min_length=1), limit: int = Query(30, ge=1, le=100)):
    return get_store().search(q, limit=limit)


@app.get("/api/statuses", dependencies=[Depends(require_auth)])
def statuses():
    return {"statuses": [s.value for s in SessionStatus]}


@app.get("/api/stream")
async def stream(request: Request, x_auth_token: Optional[str] = Header(default=None)):
    if auth_on:
        if not (_cookie_valid(request) or (x_auth_token and token_matches(x_auth_token, token))):
            raise HTTPException(401, "authentication required")
    global _sse_conns
    if _sse_conns >= MAX_SSE_CONNS:
        raise HTTPException(503, "too many live streams open")
    _sse_conns += 1

    async def gen():
        try:
            async for frame in event_stream(get_store(), dbs):
                yield frame
        finally:
            global _sse_conns
            _sse_conns -= 1

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── static UI ───────────────────────────────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.head("/", include_in_schema=False)
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # Never leak internals to the browser.
    return JSONResponse({"error": "internal error"}, status_code=500)
