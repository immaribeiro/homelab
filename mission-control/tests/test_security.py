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
            # Wrong token header rejected
            assert c.get("/api/overview", headers={"X-Auth-Token": "nope"}).status_code == 401
            # Correct token header accepted
            ok = c.get("/api/overview", headers={"X-Auth-Token": "test-token-123"})
            assert ok.status_code == 200
            # Login endpoint sets a cookie
            r = c.post("/api/login", json={"token": "test-token-123"})
            assert r.status_code == 200
            assert "mc_session" in r.cookies
            # Bad login rejected
            assert c.post("/api/login", json={"token": "bad"}).status_code == 401
    finally:
        os.environ.pop("MISSION_CONTROL_TOKEN", None)


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
