"""Data-layer tests: discovery, read-only access, aggregation, status."""
from __future__ import annotations

import sqlite3
import time

import pytest

from backend.db import (discover_state_dbs, load_messages, load_sessions,
                        load_thread_profile_map, resolve_agent, _connect_ro)
from backend.aggregate import Store
from backend.models import SessionStatus, infer_status


def test_discovery_finds_main_and_profiles(fake_home):
    dbs = discover_state_dbs(fake_home)
    names = [p for p, _ in dbs]
    assert "main" in names
    assert "architect" in names
    assert len(dbs) >= 2


def test_read_only_enforcement(fake_home):
    """The ro connection must refuse writes."""
    conn = _connect_ro(fake_home / "state.db")
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM sessions")
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO sessions (id, source, started_at) VALUES ('x','y',0)")
    conn.close()


def test_load_sessions_and_telegram_attribution(fake_home):
    dbs = discover_state_dbs(fake_home)
    main = next(d for p, d in dbs if p == "main")
    sessions = load_sessions(("main", main))
    by_id = {s.id: s for s in sessions}
    # Telegram session in thread 14 resolves to engineer via thread map
    thread_map = load_thread_profile_map(fake_home / "config.yaml")
    assert thread_map == {"1": "default", "3": "architect", "14": "engineer"}
    assert resolve_agent(by_id["tg_eng"], thread_map, []) == "engineer"
    # Profile-name sessions keep their explicit agent
    st = Store(dbs, thread_map=thread_map)
    st.refresh()
    by_id = {s.id: s for s in st.sessions}
    assert by_id["arch_local"].agent == "architect"
    # Multiplexed telegram with explicit title and no route in map
    assert by_id["suspended_tg"].agent == "main"


def test_status_lease_marks_working(fake_home):
    dbs = discover_state_dbs(fake_home)
    st = Store(dbs, thread_map=load_thread_profile_map(fake_home / "config.yaml"))
    st.refresh()
    by_id = {s.id: s for s in st.sessions}
    # Live turn lease -> WORKING regardless of last_activity age
    assert by_id["tg_eng"].status == SessionStatus.WORKING
    # Suspended gateway routing -> WAITING
    assert by_id["suspended_tg"].status == SessionStatus.WAITING
    # Ended session -> DONE
    assert by_id["cli_main"].status == SessionStatus.DONE
    assert by_id["cron_job"].status == SessionStatus.DONE
    # Open session, no lease, stale -> IDLE
    assert by_id["tg_arch"].status == SessionStatus.IDLE


def test_infer_status_unit():
    now = time.time()
    assert infer_status(ended_at=now, end_reason="done", last_activity_at=now,
                        message_count=5) == SessionStatus.DONE
    assert infer_status(ended_at=None, end_reason=None, last_activity_at=now - 5,
                        message_count=2) == SessionStatus.WORKING
    assert infer_status(ended_at=None, end_reason=None, last_activity_at=now - 9999,
                        message_count=2) == SessionStatus.IDLE
    assert infer_status(ended_at=None, end_reason=None, last_activity_at=None,
                        message_count=0) == SessionStatus.UNKNOWN


def test_infer_status_error_signals():
    """Error is detected from handoff/compression fields (real data has no
    generic 'error' end_reason)."""
    now = time.time()
    assert infer_status(ended_at=now, end_reason="done", last_activity_at=now,
                        message_count=5, handoff_state="failed") == SessionStatus.ERROR
    assert infer_status(ended_at=None, end_reason=None, last_activity_at=now,
                        message_count=1, handoff_error="boom") == SessionStatus.ERROR
    assert infer_status(ended_at=None, end_reason=None, last_activity_at=now,
                        message_count=1,
                        compression_failure_error="context too long") == SessionStatus.ERROR
    # done end_reason values observed in real data are all 'done'
    for reason in ["agent_close", "cli_close", "cron_complete", "session_reset",
                   "compression", "new_session", "ws_orphan_reap"]:
        assert infer_status(ended_at=now, end_reason=reason, last_activity_at=now,
                            message_count=1) == SessionStatus.DONE


def test_status_active_turn_token_marks_working(tmp_path):
    """gateway_routing.active_turn_token (no lease) also means working."""
    from tests.conftest import create_state_db, make_session
    import json, time as t
    now = t.time()
    db = tmp_path / "state.db"
    create_state_db(
        db,
        sessions=[make_session("turn_sess", source="telegram", title="Main",
                               thread_id="1", msgs=2, last_activity=now - 9999)],
        routing=[("/f", "k", {"session_id": "turn_sess", "suspended": False,
                              "resume_pending": False,
                              "active_turn_token": "tok-1",
                              "active_turn_started_at": now - 10}, now)],
    )
    from backend.aggregate import Store
    st = Store([("main", db)], thread_map={"1": "main"})
    st.refresh()
    assert st.sessions[0].status == SessionStatus.WORKING


def test_messages_and_children(fake_home):
    dbs = discover_state_dbs(fake_home)
    st = Store(dbs, thread_map={})
    st.refresh()
    msgs = st.messages("cli_main")
    assert len(msgs) == 4
    roles = [m.role for m in msgs]
    assert roles == ["user", "assistant", "assistant", "tool"]
    kids = st.children("cli_main")
    assert [k.id for k in kids] == ["sub_child"]


def test_overview_shapes(fake_home):
    dbs = discover_state_dbs(fake_home)
    st = Store(dbs, thread_map={})
    st.refresh()
    ov = st.overview()
    assert ov["stats"]["sessions"] == 7
    assert ov["stats"]["agents"] == 3  # main, architect, engineer
    assert ov["stats"]["tool_calls"] == 37
    sources = ov["source_counts"]
    assert sources.get("telegram") == 3
    assert sources.get("cron") == 1
    agents = {a["name"]: a for a in ov["agents"]}
    assert "engineer" in agents
    assert "architect" in agents


def test_db_error_isolation(fake_home, tmp_path):
    """A corrupt DB must not break the whole store."""
    bad = tmp_path / "bad" / "state.db"
    bad.parent.mkdir()
    bad.write_bytes(b"this is not sqlite")
    dbs = discover_state_dbs(fake_home) + [("bad", bad)]
    st = Store(dbs, thread_map={})
    st.refresh()
    assert st.errors  # the bad DB is reported
    assert len(st.sessions) == 7  # good DBs still loaded
