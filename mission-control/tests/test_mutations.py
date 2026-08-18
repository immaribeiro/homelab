"""Narrow mutation coverage for Mission Control's explicit write paths."""
from __future__ import annotations

import sqlite3
import time

from fastapi.testclient import TestClient

from backend.db import delete_session, set_session_archived
from conftest import create_state_db, make_message, make_session


def test_archive_unarchive_round_trip(tmp_path):
    path = tmp_path / "state.db"
    create_state_db(path, sessions=[make_session("archive-me")])
    db = ("main", path)
    assert set_session_archived(db, "archive-me", True)
    assert set_session_archived(db, "archive-me", False)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT archived FROM sessions WHERE id='archive-me'").fetchone()[0] == 0


def test_delete_removes_session_and_messages(tmp_path):
    path = tmp_path / "state.db"
    create_state_db(path, sessions=[make_session("delete-me")],
                    messages=[make_message("delete-me", "user", "bye")])
    assert delete_session(("main", path), "delete-me")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT id FROM sessions WHERE id='delete-me'").fetchone() is None
        assert conn.execute("SELECT id FROM messages WHERE session_id='delete-me'").fetchone() is None


def test_delete_confirm_and_live_lease_guards(mc_app):
    with TestClient(mc_app.app) as client:
        mismatch = client.post("/api/sessions/cli_main/delete", json={"confirm": "wrong"})
        assert mismatch.status_code == 400
        live = client.post("/api/sessions/tg_eng/delete", json={"confirm": "tg_eng"})
        assert live.status_code == 409


def test_mutations_require_auth_and_same_origin(monkeypatch, mc_app):
    monkeypatch.setattr(mc_app, "auth_on", True)
    monkeypatch.setattr(mc_app, "token", "test-token")
    client = TestClient(mc_app.app)
    assert client.post("/api/sessions/cli_main/archive", json={"archived": True}).status_code == 401
    r = client.post("/api/sessions/cli_main/archive", json={"archived": True},
                    headers={"X-Auth-Token": "test-token", "Origin": "https://evil.example"})
    assert r.status_code == 403
    # Restore the fixture row in case this test is run independently.
    client.post("/api/sessions/cli_main/archive", json={"archived": False},
                headers={"X-Auth-Token": "test-token"})
