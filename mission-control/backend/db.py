"""Data access layer over Hermes state databases.

Read paths use SQLite URI ``mode=ro``. The two narrow write helpers below are
the ONLY write paths: they touch one session row (and its message pair for
delete), deliberately avoiding any broader database mutation.
If a database is corrupt or locked, it is skipped with a warning rather than
failing the whole request.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .models import Message, Session, SessionStatus, infer_status

# Relative position of the profile directory under HERMES_HOME
PROFILES_DIR = "profiles"
MAIN_PROFILE_NAME = "main"

# Cap on messages fetched per session (defensive; sessions are usually << 2k)
MAX_MESSAGES_PER_SESSION = 5000
# Cap on sessions returned by list endpoints unless paginated
DEFAULT_SESSION_LIMIT = 500


class DbError(Exception):
    """Raised when a state database cannot be opened/queried."""


def default_hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def discover_state_dbs(home: Optional[Path] = None) -> List[Tuple[str, Path]]:
    """Return [(profile_name, path)] for every Hermes state.db found.

    The main profile's DB lives at <home>/state.db; each named profile has
    <home>/profiles/<name>/state.db.
    """
    home = home or default_hermes_home()
    found: List[Tuple[str, Path]] = []

    main_db = home / "state.db"
    if main_db.exists():
        found.append((MAIN_PROFILE_NAME, main_db))

    profiles_dir = home / PROFILES_DIR
    if profiles_dir.is_dir():
        for child in sorted(profiles_dir.iterdir()):
            db = child / "state.db"
            if db.exists():
                found.append((child.name, db))
    return found


def _connect_ro(path: Path) -> sqlite3.Connection:
    """Open a state.db strictly read-only."""
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    # Never let a query blow past a few seconds on a busy gateway DB.
    conn.execute("PRAGMA busy_timeout = 1500")
    return conn


def _query(path: Path, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    """Run a read-only query against one state.db."""
    conn = None
    try:
        conn = _connect_ro(path)
        return list(conn.execute(sql, params))
    except sqlite3.Error as exc:
        raise DbError(f"{path.name}: {exc}") from exc
    finally:
        if conn is not None:
            conn.close()


def set_session_archived(db: Tuple[str, Path], session_id: str, archived: bool) -> bool:
    """Set one session's archived flag using the deliberately narrow RW path."""
    _, path = db
    conn = None
    try:
        conn = sqlite3.connect(str(path), timeout=2.0)
        conn.execute("PRAGMA busy_timeout = 1500")
        cur = conn.execute("UPDATE sessions SET archived = ? WHERE id = ?",
                           (1 if archived else 0, session_id))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error as exc:
        if conn is not None:
            conn.rollback()
        raise DbError(f"{path.name}: {exc}") from exc
    finally:
        if conn is not None:
            conn.close()


def delete_session(db: Tuple[str, Path], session_id: str) -> bool:
    """Delete one session and its messages atomically."""
    _, path = db
    conn = None
    try:
        conn = sqlite3.connect(str(path), timeout=2.0)
        conn.execute("PRAGMA busy_timeout = 1500")
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error as exc:
        if conn is not None:
            conn.rollback()
        raise DbError(f"{path.name}: {exc}") from exc
    finally:
        if conn is not None:
            conn.close()


# ── sessions ────────────────────────────────────────────────────────────

_SESSION_COLS = [
    "id", "source", "user_id", "model", "parent_session_id",
    "started_at", "ended_at", "end_reason", "message_count", "tool_call_count",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
    "reasoning_tokens", "estimated_cost_usd", "title", "chat_id", "chat_type",
    "thread_id", "cwd", "git_branch", "git_repo_root", "archived", "hidden",
    "pinned", "origin_json", "profile_name", "last_activity_at",
    "last_activity_description", "handoff_state", "handoff_error",
    "compression_failure_error",
]

_SESSION_SELECT = ", ".join(_SESSION_COLS)


def _row_to_session(row: sqlite3.Row, profile: str, now: float) -> Session:
    s = Session(
        id=row["id"],
        source=row["source"] or "unknown",
        profile=row["profile_name"] or None,
        model=row["model"] or "",
        title=row["title"] or "",
        user_id=row["user_id"],
        parent_session_id=row["parent_session_id"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        end_reason=row["end_reason"],
        last_activity_at=row["last_activity_at"] or row["started_at"],
        last_activity_description=row["last_activity_description"],
        handoff_state=row["handoff_state"],
        handoff_error=row["handoff_error"],
        compression_failure_error=row["compression_failure_error"],
        message_count=row["message_count"] or 0,
        tool_call_count=row["tool_call_count"] or 0,
        input_tokens=row["input_tokens"] or 0,
        output_tokens=row["output_tokens"] or 0,
        cache_read_tokens=row["cache_read_tokens"] or 0,
        cache_write_tokens=row["cache_write_tokens"] or 0,
        reasoning_tokens=row["reasoning_tokens"] or 0,
        estimated_cost_usd=row["estimated_cost_usd"],
        chat_id=row["chat_id"],
        chat_type=row["chat_type"],
        thread_id=row["thread_id"],
        cwd=row["cwd"],
        git_branch=row["git_branch"],
        git_repo_root=row["git_repo_root"],
        archived=bool(row["archived"]),
        hidden=bool(row["hidden"]),
        pinned=bool(row["pinned"]),
        origin_json=row["origin_json"],
        db=profile,
        agent=profile,  # placeholder; refined by the aggregator
    )
    s.status = infer_status(
        ended_at=s.ended_at, end_reason=s.end_reason,
        last_activity_at=s.last_activity_at, message_count=s.message_count,
        handoff_state=s.handoff_state, handoff_error=s.handoff_error,
        compression_failure_error=s.compression_failure_error,
        now=now,
    )
    return s


def load_sessions(db: Tuple[str, Path], now: Optional[float] = None) -> List[Session]:
    """Load every session from one state.db (main or a named profile)."""
    profile, path = db
    now = now if now is not None else time.time()
    rows = _query(
        path,
        f"SELECT {_SESSION_SELECT} FROM sessions "
        "WHERE hidden = 0 ORDER BY started_at DESC",
    )
    return [_row_to_session(r, profile, now) for r in rows]


def load_session(db: Tuple[str, Path], session_id: str) -> Optional[Session]:
    profile, path = db
    rows = _query(
        path,
        f"SELECT {_SESSION_SELECT} FROM sessions WHERE id = ? LIMIT 1",
        (session_id,),
    )
    if not rows:
        return None
    return _row_to_session(rows[0], profile, time.time())


# ── messages ────────────────────────────────────────────────────────────

def load_messages(db: Tuple[str, Path], session_id: str) -> List[Message]:
    """Load messages for a session in chronological order."""
    _, path = db
    rows = _query(
        path,
        "SELECT id, session_id, role, content, tool_call_id, tool_calls, "
        "tool_name, timestamp, token_count, finish_reason, reasoning, "
        "platform_message_id, active, compacted, display_kind, api_content "
        "FROM messages WHERE session_id = ? ORDER BY timestamp ASC, id ASC "
        "LIMIT ?",
        (session_id, MAX_MESSAGES_PER_SESSION),
    )
    return [
        Message(
            id=r["id"], session_id=r["session_id"], role=r["role"],
            content=r["content"], tool_call_id=r["tool_call_id"],
            tool_calls=r["tool_calls"], tool_name=r["tool_name"],
            timestamp=r["timestamp"], token_count=r["token_count"],
            finish_reason=r["finish_reason"], reasoning=r["reasoning"],
            platform_message_id=r["platform_message_id"],
            active=bool(r["active"]), compacted=bool(r["compacted"]),
            display_kind=r["display_kind"], api_content=r["api_content"],
        )
        for r in rows
    ]


# ── subagents ───────────────────────────────────────────────────────────

def load_child_sessions(db: Tuple[str, Path], parent_id: str) -> List[Session]:
    """Direct child sessions (subagents) spawned by a parent session."""
    profile, path = db
    now = time.time()
    rows = _query(
        path,
        f"SELECT {_SESSION_SELECT} FROM sessions "
        "WHERE parent_session_id = ? ORDER BY started_at ASC",
        (parent_id,),
    )
    return [_row_to_session(r, profile, now) for r in rows]


# ── turn leases + gateway routing (authoritative activity signals) ────

def load_turn_leases(db: Tuple[str, Path]) -> Dict[str, tuple]:
    """{session_id: (acquired_at, expires_at)} from session_turn_leases.

    A lease that has not expired means the gateway is actively running that
    session's turn right now — the authoritative 'working' signal.
    """
    _, path = db
    try:
        rows = _query(
            path,
            "SELECT conversation_id, acquired_at, expires_at "
            "FROM session_turn_leases",
        )
    except DbError:
        return {}
    return {r["conversation_id"]: (r["acquired_at"], r["expires_at"]) for r in rows}


def load_gateway_routing(db: Tuple[str, Path]) -> Dict[str, dict]:
    """{session_id: {suspended, resume_pending, active_turn_started_at}}.

    Parsed from gateway_routing.entry_json (per-channel gateway state).
    """
    _, path = db
    try:
        rows = _query(path, "SELECT entry_json FROM gateway_routing")
    except DbError:
        return {}
    import json
    out: Dict[str, dict] = {}
    for r in rows:
        try:
            e = json.loads(r["entry_json"])
        except (TypeError, ValueError):
            continue
        sid = e.get("session_id")
        if not sid:
            continue
        out[sid] = {
            "suspended": bool(e.get("suspended")),
            "resume_pending": bool(e.get("resume_pending")),
            "active_turn_token": e.get("active_turn_token"),
            "active_turn_started_at": e.get("active_turn_started_at"),
        }
    return out


# ── trends (per-day activity/cost rollup) ──────────────────────────────

def load_trends(db: Tuple[str, Path], since: float) -> List[tuple]:
    """(started_at, message_count, tool_call_count, input_tokens,
    output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens,
    estimated_cost_usd) rows for sessions started at/after `since`."""
    with _connect_ro(db[1]) as conn:
        cur = conn.execute(
            "SELECT started_at, message_count, tool_call_count, "
            "input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, "
            "reasoning_tokens, COALESCE(estimated_cost_usd, 0) "
            "FROM sessions WHERE started_at >= ? ORDER BY started_at",
            (since,),
        )
        return [tuple(r) for r in cur.fetchall()]


# ── FTS search ──────────────────────────────────────────────────────────

def _safe_fts_term(term: str) -> str:
    """Wrap a user term so it can't break FTS5 syntax.

    Quoting a phrase makes special characters inert; trigram tables also
    tolerate quoting well.
    """
    # Double quotes are the only thing FTS5 treats structurally in a phrase;
    # strip them first, then collapse whitespace, so we can't break out.
    cleaned = term.replace('"', " ")
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return ""
    return f'"{cleaned}"'


def search_messages(db: Tuple[str, Path], term: str, limit: int = 50) -> List[dict]:
    """Full-text search over message content using the trigram FTS index.

    Returns [{session_id, message_id, role, snippet, timestamp}] ordered by
    recency. The trigram index gives substring matching without FTS5 query
    syntax errors.
    """
    _, path = db
    q = _safe_fts_term(term)
    if not q:
        return []
    try:
        rows = _query(
            path,
            "SELECT m.id AS message_id, m.session_id, m.role, m.timestamp, "
            "   snippet(messages_fts_trigram, 0, '[', ']', '…', 12) AS snippet "
            "FROM messages_fts_trigram "
            "JOIN messages m ON m.id = messages_fts_trigram.rowid "
            "WHERE messages_fts_trigram MATCH ? "
            "ORDER BY m.timestamp DESC LIMIT ?",
            (q, limit),
        )
    except DbError:
        # Fall back to LIKE if the trigram table is unavailable.
        rows = _query(
            path,
            "SELECT id AS message_id, session_id, role, timestamp, "
            "substr(content, 1, 200) AS snippet "
            "FROM messages WHERE content LIKE ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (f"%{term}%", limit),
        )
    return [dict(r) for r in rows]


def search_sessions(db: Tuple[str, Path], term: str, limit: int = 50) -> List[dict]:
    """LIKE search over session metadata (title, model, id, source)."""
    _, path = db
    like = f"%{term}%"
    rows = _query(
        path,
        f"SELECT {_SESSION_SELECT} FROM sessions "
        "WHERE title LIKE ? OR model LIKE ? OR id LIKE ? OR source LIKE ? "
        "ORDER BY started_at DESC LIMIT ?",
        (like, like, like, like, limit),
    )
    return [dict(r) for r in rows]


# ── profile mapping (thread_id -> profile) ──────────────────────────────

def load_thread_profile_map(config_path: Optional[Path] = None) -> Dict[str, str]:
    """Read gateway.profile_routes from the main config.yaml.

    Returns {thread_id: profile_name} for Telegram forum topics. This is how
    multiplexed Telegram sessions (stored centrally in the main state.db with
    profile_name NULL) are attributed to their agent.
    """
    if config_path is None:
        config_path = default_hermes_home() / "config.yaml"
    mapping: Dict[str, str] = {}
    if not config_path.exists():
        return mapping
    try:
        import yaml  # available in the Hermes venv
        with open(config_path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        routes = (cfg.get("gateway") or {}).get("profile_routes") or []
        for route in routes:
            if route.get("platform") == "telegram" and route.get("thread_id"):
                mapping[str(route["thread_id"])] = route.get("profile", "main")
    except Exception:
        # Never fail the API because the config couldn't be parsed.
        pass
    return mapping


def resolve_agent(session: Session, thread_map: Dict[str, str],
                  telegram_titles: Iterable[str]) -> str:
    """Resolve which agent/profile a session belongs to.

    Priority:
      1. sessions.profile_name (explicit, set by the profile's own runtime)
      2. Telegram forum topic: thread_id -> profile from gateway config
      3. Telegram session titled with an agent name (multiplexer titles
         sessions after the routed profile)
      4. main
    """
    if session.profile:
        # Canonicalize: the main profile may record 'default' (config name).
        return "main" if session.profile == "default" else session.profile
    if session.source == "telegram":
        if session.thread_id and session.thread_id in thread_map:
            resolved = thread_map[session.thread_id]
            # config uses profile name 'default' for the main profile; the
            # canonical agent name is 'main'.
            return "main" if resolved == "default" else resolved
        title = (session.title or "").strip()
        if title:
            for name in telegram_titles:
                if title.lower() == name.lower():
                    # Titles are agent display names; canonical profile names
                    # are lowercase (e.g. 'Main' -> 'main').
                    return name.lower()
    return MAIN_PROFILE_NAME
