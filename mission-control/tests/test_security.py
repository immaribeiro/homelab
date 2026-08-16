"""Security tests: auth fail-closed, read-only guarantees, no secret leakage."""
from __future__ import annotations

import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.auth import auth_enabled, load_or_create_token
from backend.db import _connect_ro


def test_auth_enabled_fail_closed():
    # Non-loopback bind without a token must still require auth (fail closed)
    assert auth_enabled("0.0.0.0", None) is True
    assert auth_enabled("100.101.63.91", None) is True
    # Loopback without token stays open
    assert auth_enabled("127.0.0.1", None) is False
    # Any token enables auth everywhere
    assert auth_enabled("127.0.0.1", "sekret") is True


def test_token_creation_and_rotation(tmp_path):
    t1 = load_or_create_token(tmp_path, force=True)
    assert len(t1) >= 20
    t2 = load_or_create_token(tmp_path, force=True)
    assert t2 == t1  # persisted, stable
    assert (tmp_path / "token").stat().st_mode & 0o777 == 0o600
    # loopback without force -> no token created
    empty = load_or_create_token(tmp_path / "other", force=False)
    assert empty == ""


def test_token_file_permissions_repaired_on_read(tmp_path):
    """A pre-existing token file with loose perms gets repaired to 0600."""
    tf = tmp_path / "token"
    tf.write_text("some-token-value\n", encoding="utf-8")
    tf.chmod(0o644)
    tok = load_or_create_token(tmp_path, force=True)
    assert tok == "some-token-value"
    assert (tmp_path / "token").stat().st_mode & 0o777 == 0o600


def test_message_payload_truncation(fake_home, mc_app):
    """Oversized message content is clipped server-side (bounded payloads)."""
    import sqlite3
    conn = sqlite3.connect(str(fake_home / "state.db"))
    big = "x" * 100_000
    conn.execute("INSERT INTO messages (session_id, role, content, timestamp) "
                 "VALUES ('cli_main', 'assistant', ?, 1.0)", (big,))
    conn.commit()
    conn.close()
    with TestClient(mc_app.app) as c:
        d = c.get("/api/sessions/cli_main").json()
        contents = [m.get("content") or "" for m in d["messages"]]
        assert any(len(x) == 100_000 for x in contents) is False
        assert all(len(x) <= 20_000 + 200 for x in contents)


def test_readonly_connection_refuses_all_writes(fake_home):
    conn = _connect_ro(fake_home / "state.db")
    for stmt in [
        "UPDATE sessions SET title='x'",
        "DELETE FROM messages",
        "INSERT INTO sessions (id, source, started_at) VALUES ('a','b',0)",
        "DROP TABLE sessions",
    ]:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(stmt)
    conn.close()


def test_api_auth_blocks_when_token_set(fake_home, mc_app):
    os.environ["MISSION_CONTROL_TOKEN"] = "test-token-123"
    try:
        with TestClient(mc_app.app) as c:
            assert c.get("/api/overview").status_code == 401
            assert c.get("/api/sessions").status_code == 401
            # Public endpoints stay minimal even when auth is on
            assert c.get("/api/health").json() == {"ok": True}
            pub = c.get("/api/config").json()
            assert "profiles" not in pub and "hermes_home" not in pub
            # /api/info requires auth
            assert c.get("/api/info").status_code == 401
            # Wrong token header rejected
            assert c.get("/api/overview", headers={"X-Auth-Token": "nope"}).status_code == 401
            # Correct token header accepted
            ok = c.get("/api/overview", headers={"X-Auth-Token": "test-token-123"})
            assert ok.status_code == 200
            assert c.get("/api/info", headers={"X-Auth-Token": "test-token-123"}).status_code == 200
            # Login endpoint sets a cookie
            r = c.post("/api/login", json={"token": "test-token-123"})
            assert r.status_code == 200
            assert "mc_session" in r.cookies
            # Bad login rejected
            assert c.post("/api/login", json={"token": "bad"}).status_code == 401
    finally:
        os.environ.pop("MISSION_CONTROL_TOKEN", None)


def test_sse_connection_cap(mc_app):
    """The SSE endpoint refuses to open more than MAX_SSE_CONNS streams."""
    with TestClient(mc_app.app) as c:
        mc_app._sse_conns = mc_app.MAX_SSE_CONNS
        try:
            r = c.get("/api/stream")
            assert r.status_code == 503
        finally:
            mc_app._sse_conns = 0


def test_api_open_on_loopback_without_token(mc_app):
    with TestClient(mc_app.app) as c:
        assert c.get("/api/overview").status_code == 200
        assert c.get("/api/sessions").status_code == 200


def test_api_never_leaks_secrets(mc_app):
    """Responses must not contain credential material from the fake home."""
    with TestClient(mc_app.app) as c:
        ov = c.get("/api/overview").json()
        blob = str(ov)
        assert "TELEGRAM_BOT_TOKEN" not in blob
        assert "api_key" not in blob.lower() or "api_call_count" in blob
        d = c.get("/api/sessions/cli_main").json()
        # messages include tool args but no credential fields exist in schema;
        # ensure we never serialize .env contents
        assert "OPENAI_API_KEY" not in str(d)


def test_sql_injection_attempts(mc_app):
    """Filter values are parameterized/escaped — injection must not crash or
    leak extra rows."""
    with TestClient(mc_app.app) as c:
        r = c.get("/api/sessions", params={"agent": "x' OR '1'='1"})
        assert r.status_code == 200
        assert r.json()["total"] == 0
        r2 = c.get("/api/sessions", params={"q": "' OR 1=1 --"})
        assert r2.status_code == 200


def test_static_pages_served(mc_app):
    with TestClient(mc_app.app) as c:
        assert c.get("/").status_code == 200
        assert "text/html" in c.get("/").headers["content-type"]
        assert c.get("/static/app.js").status_code == 200
        assert c.get("/static/style.css").status_code == 200


def test_security_headers(mc_app):
    with TestClient(mc_app.app) as c:
        r = c.get("/")
        assert "Content-Security-Policy" in r.headers
        assert "script-src 'self'" in r.headers["Content-Security-Policy"]
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        api_r = c.get("/api/overview")
        assert api_r.headers.get("Cache-Control") == "no-store"
        assert api_r.headers.get("X-Content-Type-Options") == "nosniff"


def test_db_hashes_unchanged_after_api(fake_home, mc_app):
    """Prove strict read-only-ness: every state.db byte is identical before
    and after exercising the API (list, detail, search, agents, sources)."""
    import hashlib

    def snap():
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for _, p in __import__("backend.db", fromlist=["discover_state_dbs"]).discover_state_dbs(fake_home)}

    before = snap()
    with TestClient(mc_app.app) as c:
        assert c.get("/api/overview").status_code == 200
        assert c.get("/api/sessions?limit=100").status_code == 200
        assert c.get("/api/sessions/cli_main").status_code == 200
        assert c.get("/api/search", params={"q": "CVE"}).status_code == 200
        assert c.get("/api/agents").status_code == 200
        assert c.get("/api/sources").status_code == 200
    after = snap()
    assert before == after


def test_stream_emits_event_and_is_read_only(fake_home):
    """The SSE generator emits a refresh event on first iteration and never
    writes. Tested directly (TestClient hangs on infinite streams)."""
    import asyncio

    from backend.aggregate import Store
    from backend.db import discover_state_dbs
    from backend.stream import event_stream

    dbs = discover_state_dbs(fake_home)
    st = Store(dbs, thread_map={})
    st.refresh()
    import hashlib
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for _, p in dbs}

    async def first_event():
        agen = event_stream(st, dbs)
        async for ev in agen:
            return ev

    ev = asyncio.get_event_loop().run_until_complete(
        asyncio.wait_for(first_event(), timeout=10))
    assert ev.startswith("event: refresh")
    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for _, p in dbs}
    assert before == after
