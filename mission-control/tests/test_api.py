"""API tests via FastAPI TestClient against the fake Hermes home."""
from __future__ import annotations

from fastapi.testclient import TestClient


def _client(mc_app):
    return TestClient(mc_app.app)


def test_health_and_config(mc_app):
    with _client(mc_app) as c:
        h = c.get("/api/health").json()
        assert h == {"ok": True}  # minimal, no deployment metadata
        cfg = c.get("/api/config").json()
        assert cfg["app"] == "Hermes Mission Control"
        assert "auth" in cfg
        # Public config must not leak profiles / paths / versions
        assert "profiles" not in cfg
        assert "hermes_home" not in cfg
        assert "version" not in cfg
        # Full details live behind auth (/api/info) — open in loopback mode
        info = c.get("/api/info").json()
        assert "main" in info["profiles"]
        assert "architect" in info["profiles"]
        assert "password" not in str(info).lower()
        assert "secret" not in str(info).lower()


def test_overview_endpoint(mc_app):
    with _client(mc_app) as c:
        ov = c.get("/api/overview").json()
        assert ov["stats"]["sessions"] == 7
        assert ov["stats"]["agents"] == 3  # main, architect, engineer
        assert "working" in ov["status_counts"]
        agents = {a["name"]: a for a in ov["agents"]}
        assert "engineer" in agents
        assert agents["engineer"]["total_sessions"] == 1


def test_trends_endpoint(mc_app):
    with TestClient(mc_app.app) as c:
        r = c.get("/api/trends?days=7").json()
        assert len(r["points"]) == 7
        assert all({"date", "sessions", "messages", "tool_calls", "tokens", "cost_usd"} <= set(p) for p in r["points"])
        total = sum(p["sessions"] for p in r["points"])
        assert total >= 7  # fixture sessions all start "now"
        # clamping: absurd day counts are rejected
        assert len(c.get("/api/trends?days=99999").json()["points"]) == 90


def test_sessions_filters(mc_app):
    with _client(mc_app) as c:
        all_s = c.get("/api/sessions?limit=100").json()
        assert all_s["total"] == 7
        tg = c.get("/api/sessions?source=telegram").json()
        assert tg["total"] == 3
        eng = c.get("/api/sessions?agent=engineer").json()
        assert eng["total"] == 1
        assert eng["sessions"][0]["source"] == "telegram"
        working = c.get("/api/sessions?status=working").json()
        assert working["total"] == 1
        done = c.get("/api/sessions?status=done").json()
        assert done["total"] == 4  # cli_main, cron_job, sub_child, arch_local
        cron = c.get("/api/sessions?source=cron").json()
        assert cron["total"] == 1
        # combined filters
        both = c.get("/api/sessions?source=telegram&status=working").json()
        assert both["total"] == 1


def test_session_detail(mc_app):
    with _client(mc_app) as c:
        d = c.get("/api/sessions/cli_main").json()
        assert d["title"] == "CVE-2026 research"
        assert d["agent"] == "main"
        assert len(d["messages"]) == 4
        assert len(d["children"]) == 1
        assert d["children"][0]["id"] == "sub_child"
        assert c.get("/api/sessions/does-not-exist").status_code == 404


def test_session_messages_include_tool_calls(mc_app):
    with _client(mc_app) as c:
        d = c.get("/api/sessions/cli_main").json()
        tool_msgs = [m for m in d["messages"] if m["tool_calls"]]
        assert tool_msgs
        assert "web_search" in tool_msgs[0]["tool_calls"]


def test_search_endpoint(mc_app):
    with _client(mc_app) as c:
        res = c.get("/api/search", params={"q": "CVE-2026"}).json()
        assert res["messages"] and res["sessions"]
        assert c.get("/api/search", params={"q": ""}).status_code == 422
        hostile = c.get("/api/search", params={"q": '" OR 1=1 --'}).json()
        assert "messages" in hostile


def test_agents_and_sources(mc_app):
    with _client(mc_app) as c:
        agents = c.get("/api/agents").json()["agents"]
        names = {a["name"] for a in agents}
        assert "main" in names and "engineer" in names and "architect" in names
        sources = {s["source"] for s in c.get("/api/sources").json()["sources"]}
        assert {"telegram", "cli", "cron", "desktop"} <= sources


def test_statuses_endpoint(mc_app):
    with _client(mc_app) as c:
        st = c.get("/api/statuses").json()["statuses"]
        assert "working" in st and "waiting" in st and "done" in st
