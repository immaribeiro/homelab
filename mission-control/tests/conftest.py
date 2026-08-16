"""Shared fixtures: a fake Hermes home (state DBs + config) and a TestClient."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional

import pytest

# Ensure the project root is importable regardless of CWD.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SESSION_COLS = [
    "id TEXT PRIMARY KEY", "source TEXT NOT NULL", "user_id TEXT",
    "model TEXT", "model_config TEXT", "system_prompt TEXT",
    "parent_session_id TEXT", "started_at REAL NOT NULL", "ended_at REAL",
    "end_reason TEXT", "message_count INTEGER DEFAULT 0",
    "tool_call_count INTEGER DEFAULT 0",
    "input_tokens INTEGER DEFAULT 0", "output_tokens INTEGER DEFAULT 0",
    "cache_read_tokens INTEGER DEFAULT 0", "cache_write_tokens INTEGER DEFAULT 0",
    "reasoning_tokens INTEGER DEFAULT 0", "billing_provider TEXT",
    "estimated_cost_usd REAL", "title TEXT", "chat_id TEXT", "chat_type TEXT",
    "thread_id TEXT", "cwd TEXT", "git_branch TEXT", "git_repo_root TEXT",
    "archived INTEGER DEFAULT 0", "hidden INTEGER DEFAULT 0",
    "pinned INTEGER DEFAULT 0", "origin_json TEXT", "profile_name TEXT",
    "last_activity_at REAL", "last_activity_description TEXT",
]

MESSAGE_COLS = [
    "id INTEGER PRIMARY KEY AUTOINCREMENT", "session_id TEXT NOT NULL",
    "role TEXT NOT NULL", "content TEXT", "tool_call_id TEXT",
    "tool_calls TEXT", "tool_name TEXT", "timestamp REAL NOT NULL",
    "token_count INTEGER", "finish_reason TEXT", "reasoning TEXT",
    "platform_message_id TEXT", "active INTEGER DEFAULT 1",
    "compacted INTEGER DEFAULT 0", "display_kind TEXT", "api_content TEXT",
]


def create_state_db(path: Path, sessions=None, messages=None, leases=None,
                    routing=None, with_fts: bool = True) -> None:
    """Build a state.db that mirrors the real Hermes schema (subset)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE sessions (" + ", ".join(SESSION_COLS) + ")")
    conn.execute("CREATE TABLE messages (" + ", ".join(MESSAGE_COLS) + ")")
    conn.execute("CREATE INDEX idx_messages_session ON messages(session_id, timestamp)")
    if with_fts:
        try:
            conn.execute("CREATE VIRTUAL TABLE messages_fts USING fts5(content)")
            conn.execute("CREATE VIRTUAL TABLE messages_fts_trigram "
                         "USING fts5(content, tokenize='trigram')")
        except sqlite3.OperationalError:
            with_fts = False
    conn.execute("CREATE TABLE session_turn_leases ("
                 "conversation_id TEXT PRIMARY KEY, holder TEXT NOT NULL, "
                 "acquired_at REAL NOT NULL, expires_at REAL NOT NULL)")
    conn.execute("CREATE TABLE gateway_routing ("
                 "scope TEXT NOT NULL DEFAULT '', session_key TEXT NOT NULL, "
                 "entry_json TEXT NOT NULL, updated_at REAL NOT NULL, "
                 "PRIMARY KEY (scope, session_key))")
    for s in sessions or []:
        cols = [c.split()[0] for c in SESSION_COLS]
        vals = [s.get(c) for c in cols]
        conn.execute("INSERT INTO sessions (" + ", ".join(cols) + ") VALUES ("
                     + ", ".join("?" for _ in cols) + ")", vals)
    for m in messages or []:
        cols = [c.split()[0] for c in MESSAGE_COLS]
        vals = [m.get(c) for c in cols]
        conn.execute("INSERT INTO messages (" + ", ".join(cols) + ") VALUES ("
                     + ", ".join("?" for _ in cols) + ")", vals)
        if with_fts:
            rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            content = f"{m.get('content') or ''} {m.get('tool_name') or ''}"
            conn.execute("INSERT INTO messages_fts_trigram(rowid, content) VALUES (?, ?)",
                         (rowid, content))
    for conv, holder, acquired, expires in leases or []:
        conn.execute("INSERT INTO session_turn_leases VALUES (?, ?, ?, ?)",
                     (conv, holder, acquired, expires))
    for scope, key, entry, updated in routing or []:
        conn.execute("INSERT INTO gateway_routing VALUES (?, ?, ?, ?)",
                     (scope, key, json.dumps(entry), updated))
    conn.commit()
    conn.close()


def make_session(sid: str, *, source="cli", model="test/model", title="T",
                 started=None, ended=None, end_reason=None, agent=None,
                 thread_id=None, parent=None, last_activity=None, msgs=0,
                 tools=0) -> dict:
    now = time.time()
    return {
        "id": sid, "source": source, "model": model, "title": title,
        "started_at": started or (now - 1000), "ended_at": ended,
        "end_reason": end_reason, "parent_session_id": parent,
        "thread_id": thread_id, "profile_name": agent,
        "last_activity_at": last_activity or now,
        "message_count": msgs, "tool_call_count": tools,
        "input_tokens": 100, "output_tokens": 50,
        "archived": 0, "hidden": 0, "pinned": 0,
    }


def make_message(sid: str, role: str, content: str, ts: Optional[float] = None, *,
                 tool_name=None, tool_calls=None) -> dict:
    now = time.time()
    return {
        "session_id": sid, "role": role, "content": content,
        "tool_name": tool_name, "tool_calls": tool_calls,
        "timestamp": ts or now,
    }


@pytest.fixture(scope="session")
def fake_home(tmp_path_factory) -> Path:
    home = tmp_path_factory.mktemp("hermes_home")
    now = time.time()

    # Main profile DB
    create_state_db(
        home / "state.db",
        sessions=[
            make_session("tg_eng", source="telegram", title="Engineer",
                         thread_id="14", model="deepseek/deepseek-v4-flash",
                         msgs=12, tools=5, last_activity=now - 20),
            make_session("tg_arch", source="telegram", title="Architect",
                         thread_id="3", model="z-ai/glm-5.2",
                         msgs=8, tools=3, last_activity=now - 600),
            make_session("cli_main", source="cli", title="CVE-2026 research",
                         model="gpt-5.6-luna", msgs=40, tools=17,
                         ended=now - 3600, end_reason="done",
                         last_activity=now - 3600),
            make_session("cron_job", source="cron", title="Daily research",
                         model="deepseek/deepseek-v4-flash", msgs=7, tools=2,
                         ended=now - 7200, end_reason="done"),
            make_session("sub_child", source="cli", title="Web Research",
                         model="gpt-5.6-luna", parent="cli_main",
                         msgs=5, tools=4, ended=now - 3500, end_reason="done"),
            make_session("suspended_tg", source="telegram", title="Main",
                         thread_id="1", msgs=3, tools=0,
                         last_activity=now - 300),
        ],
        messages=[
            make_message("cli_main", "user", "Investigate CVE-2026-1234 please", ts=now - 3700),
            make_message("cli_main", "assistant", "Checking advisories", ts=now - 3690),
            make_message("cli_main", "assistant", "", tool_name=None,
                         tool_calls=json.dumps([{"function": {"name": "web_search",
                                                              "arguments": "{\"q\": \"CVE-2026-1234\"}"}}]),
                         ts=now - 3680),
            make_message("cli_main", "tool", '{"results": []}', tool_name="web_search", ts=now - 3670),
            make_message("tg_eng", "user", "check the k3s cluster", ts=now - 30),
            make_message("tg_eng", "assistant", "Running kubectl get pods", ts=now - 25),
        ],
        leases=[("tg_eng", "pid=999:turn=tg_eng", now - 5, now + 60)],
        routing=[
            ("/fake", "agent:main:telegram:group:-100:1",
             {"session_id": "suspended_tg", "suspended": True,
              "resume_pending": False, "active_turn_started_at": None},
             now),
        ],
    )

    # Named profile DB
    create_state_db(
        home / "profiles" / "architect" / "state.db",
        sessions=[
            make_session("arch_local", source="desktop", title="ADR review",
                         model="deepseek/deepseek-v4-pro-0813", agent="architect",
                         msgs=15, tools=6, ended=now - 5000, end_reason="done"),
        ],
        messages=[make_message("arch_local", "user", "review this ADR", ts=now - 5100)],
    )
    (home / "profiles" / "architect").mkdir(parents=True, exist_ok=True)

    # Config with telegram profile routes (mirrors the live one)
    (home / "config.yaml").write_text(
        "gateway:\n"
        "  multiplex_profiles: true\n"
        "  profile_routes:\n"
        "    - name: tg-general\n      platform: telegram\n"
        "      chat_id: '-1004449482428'\n      thread_id: '1'\n      profile: default\n"
        "    - name: tg-architect\n      platform: telegram\n"
        "      chat_id: '-1004449482428'\n      thread_id: '3'\n      profile: architect\n"
        "    - name: tg-engineer\n      platform: telegram\n"
        "      chat_id: '-1004449482428'\n      thread_id: '14'\n      profile: engineer\n",
        encoding="utf-8",
    )
    return home


@pytest.fixture(scope="session")
def mc_app(fake_home: Path):
    """Backend API app pointed at the fake home (fresh import, env-scoped)."""
    os.environ["HERMES_HOME"] = str(fake_home)
    os.environ["MISSION_CONTROL_DATA_DIR"] = str(fake_home / "mc-data")
    os.environ.pop("MISSION_CONTROL_TOKEN", None)
    os.environ["MISSION_CONTROL_HOST"] = "127.0.0.1"

    from backend import api as api_mod
    mod = sys.modules["backend.api"]
    import importlib
    importlib.reload(mod)
    return mod
