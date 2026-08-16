"""Session export endpoint tests: contract, formats, auth, read-only, secrets."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3

from fastapi.testclient import TestClient

from backend.db import discover_state_dbs
from tests.conftest import SESSION_COLS, make_session


def _insert_session(fake_home, sess: dict) -> None:
    """Insert a session row into the fake main state.db (mirrors conftest)."""
    conn = sqlite3.connect(str(fake_home / "state.db"))
    cols = [c.split()[0] for c in SESSION_COLS]
    vals = [sess.get(c) for c in cols]
    conn.execute("INSERT INTO sessions (" + ", ".join(cols) + ") VALUES ("
                 + ", ".join("?" for _ in cols) + ")", vals)
    conn.commit()
    conn.close()


def test_export_json_contract(mc_app):
    with TestClient(mc_app.app) as c:
        r = c.get("/api/sessions/cli_main/export?format=json")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/json")
        cd = r.headers["content-disposition"]
        assert cd.startswith("attachment;")
        assert "filename=" in cd
        body = r.json()
        # Top-level contract: session + messages + children only
        assert set(body) == {"session", "messages", "children"}
        # Session reuses the standard to_dict shape
        assert body["session"]["id"] == "cli_main"
        assert body["session"]["title"] == "CVE-2026 research"
        assert body["session"]["agent"] == "main"
        # Messages reuse the standard Message.to_dict shape
        assert body["messages"]
        first = body["messages"][0]
        assert {"id", "session_id", "role", "content", "timestamp",
                "tool_calls", "reasoning", "token_count"} <= set(first)
        # Children are compact per-session descriptors
        assert body["children"] and body["children"][0]["id"] == "sub_child"
        child = body["children"][0]
        assert set(child) == {"id", "title", "status", "message_count",
                              "tool_call_count", "agent"}


def test_export_markdown_layout(mc_app):
    with TestClient(mc_app.app) as c:
        r = c.get("/api/sessions/cli_main/export?format=md")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/markdown")
        assert r.headers["content-disposition"].startswith("attachment;")
        text = r.text
        assert text.startswith("# CVE-2026 research")
        # Metadata block
        assert "**Session**: cli_main" in text
        assert "**Agent**: main" in text
        assert "**Source**: cli" in text
        assert "**Model**: gpt-5.6-luna" in text
        assert "**Started**: " in text and "**Ended**: " in text
        assert "**Messages**: " in text and "**Tool calls**: " in text
        # Messages section
        assert "## Messages" in text
        assert "**user** (" in text
        assert "> Investigate CVE-2026-1234 please" in text
        # Tool calls render as a fenced json block
        assert "```json" in text
        assert '"web_search"' in text


def test_export_default_format_and_invalid(mc_app):
    with TestClient(mc_app.app) as c:
        # No format param -> json
        r = c.get("/api/sessions/cli_main/export")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/json")
        assert set(r.json()) == {"session", "messages", "children"}
        # Explicit json works too
        assert c.get("/api/sessions/cli_main/export?format=json").status_code == 200
        # Invalid format -> 422
        assert c.get("/api/sessions/cli_main/export?format=pdf").status_code == 422
        assert c.get("/api/sessions/cli_main/export?format=XML").status_code == 422


def test_export_unknown_session_404(mc_app):
    with TestClient(mc_app.app) as c:
        assert c.get("/api/sessions/does-not-exist/export").status_code == 404
        assert c.get("/api/sessions/does-not-exist/export?format=md").status_code == 404


def test_export_preserves_full_content(fake_home, mc_app):
    """Export bypasses the UI content caps (raw=True): 50k content stays 50k."""
    conn = sqlite3.connect(str(fake_home / "state.db"))
    big = "Z" * 50_000
    reasoning = "deep thought " * 1000  # 13k chars > 10k reasoning cap
    conn.execute(
        "INSERT INTO messages (session_id, role, content, reasoning, timestamp) "
        "VALUES ('cli_main', 'assistant', ?, ?, 1.5)",
        (big, reasoning))
    conn.commit()
    conn.close()
    with TestClient(mc_app.app) as c:
        body = c.get("/api/sessions/cli_main/export?format=json").json()
        msgs = [m for m in body["messages"] if m.get("content") == big]
        assert msgs, "50k message missing from export"
        assert len(msgs[0]["content"]) == 50_000
        assert "truncated" not in msgs[0]["content"]
        # Reasoning unclipped too (would be capped at 10k in the UI path)
        assert len(msgs[0]["reasoning"]) == len(reasoning)
        # Markdown carries the full content and the italic reasoning line
        md = c.get("/api/sessions/cli_main/export?format=md").text
        assert "Z" * 100 in md
        assert "*reasoning: deep thought" in md


def test_export_no_secrets(fake_home, mc_app):
    """origin_json / api_content (secret-adjacent) never reach the output."""
    conn = sqlite3.connect(str(fake_home / "state.db"))
    conn.execute(
        "UPDATE sessions SET origin_json = ? WHERE id = 'cli_main'",
        (json.dumps({"OPENAI_API_KEY": "sk-secret123",
                     "TELEGRAM_BOT_TOKEN": "123:abc"}),))
    conn.execute(
        "INSERT INTO messages (session_id, role, content, api_content, timestamp) "
        "VALUES ('cli_main', 'assistant', 'visible export text', ?, 2.5)",
        (json.dumps({"OPENAI_API_KEY": "sk-secret456",
                     "TELEGRAM_BOT_TOKEN": "456:xyz"}),))
    conn.commit()
    conn.close()
    with TestClient(mc_app.app) as c:
        for fmt in ("json", "md"):
            text = c.get(f"/api/sessions/cli_main/export?format={fmt}").text
            for banned in ("origin_json", "api_content", "OPENAI_API_KEY",
                           "TELEGRAM_BOT_TOKEN", "sk-secret123", "sk-secret456",
                           "123:abc", "456:xyz"):
                assert banned not in text, f"{banned!r} leaked in {fmt} export"
        # Ordinary message content still exports
        out = c.get("/api/sessions/cli_main/export?format=json").text
        assert "visible export text" in out


def test_export_requires_auth_when_token_set(mc_app):
    os.environ["MISSION_CONTROL_TOKEN"] = "test-token-123"
    try:
        with TestClient(mc_app.app) as c:
            assert c.get("/api/sessions/cli_main/export").status_code == 401
            assert c.get("/api/sessions/cli_main/export?format=md").status_code == 401
            ok = c.get("/api/sessions/cli_main/export",
                       headers={"X-Auth-Token": "test-token-123"})
            assert ok.status_code == 200
            assert ok.headers["content-type"].startswith("application/json")
    finally:
        os.environ.pop("MISSION_CONTROL_TOKEN", None)


def test_export_read_only(fake_home, mc_app):
    """Export never writes: every state.db byte is identical before/after."""
    def snap():
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for _, p in discover_state_dbs(fake_home)}

    before = snap()
    with TestClient(mc_app.app) as c:
        assert c.get("/api/sessions/cli_main/export?format=json").status_code == 200
        assert c.get("/api/sessions/cli_main/export?format=md").status_code == 200
        assert c.get("/api/sessions/cli_main/export?format=json").status_code == 200
        assert c.get("/api/sessions/does-not-exist/export").status_code == 404
    after = snap()
    assert before == after


def test_export_filename_sanitized(fake_home, mc_app):
    """Slashes, whitespace (and header-breaking quotes) are stripped from the
    attachment filename."""
    _insert_session(fake_home, make_session(
        "dirty_title", title='CVE 2026 / "research"', model="test/model"))
    with TestClient(mc_app.app) as c:
        for fmt, ext in (("json", "json"), ("md", "md")):
            r = c.get(f"/api/sessions/dirty_title/export?format={fmt}")
            cd = r.headers["content-disposition"]
            assert f'filename="CVE2026research.{ext}"' in cd
            name = cd.split("filename=")[1].strip('"')
            assert "/" not in name and " " not in name and '"' not in name


def test_export_empty_title_falls_back_to_id(fake_home, mc_app):
    _insert_session(fake_home, make_session("no_title_sess", title="   ",
                                            model="test/model"))
    with TestClient(mc_app.app) as c:
        for fmt, ext in (("json", "json"), ("md", "md")):
            r = c.get(f"/api/sessions/no_title_sess/export?format={fmt}")
            cd = r.headers["content-disposition"]
            assert f'filename="no_title_sess.{ext}"' in cd
