"""Data models for Hermes Mission Control.

Maps the Hermes `sessions` / `messages` SQLite schema (discovered from the
live state.db) into plain dataclasses with computed fields (agent, status).

All timestamps in Hermes are Unix epoch floats (REAL).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Defensive payload caps: a single session detail must stay bounded even with
# pathological message sizes. Display-side truncation is the UI's job; these
# protect memory, serialization, and the wire.
MAX_CONTENT_CHARS = 20_000
MAX_REASONING_CHARS = 10_000
MAX_TOOL_CALLS_CHARS = 20_000


def _clip(value: Optional[str], cap: int) -> Optional[str]:
    if value is None or len(value) <= cap:
        return value
    return value[:cap] + f"\n…[truncated {len(value) - cap} chars]"


class SessionStatus(str, Enum):
    WORKING = "working"      # open session with activity within the active window
    WAITING = "waiting"      # open session, waiting on input/approval (inferred)
    IDLE = "idle"            # open session, no recent activity
    DONE = "done"            # ended normally
    ERROR = "error"          # ended with an error
    UNKNOWN = "unknown"      # cannot be determined


# Seconds without activity after which an open session is considered idle
# rather than working. Telegram/gateway turns can take minutes for long tool
# chains, so this is intentionally generous.
ACTIVE_WINDOW_SECONDS = 120
# An open session that has *never* produced a message is treated as idle
# rather than working regardless of recency.
STALE_WINDOW_SECONDS = 24 * 3600

# end_reason values observed / expected in Hermes sessions.
DONE_REASONS = {"done", "completed", "complete", "finished", "exit", "exited",
                "user_exit", "clean", "stop"}
ERROR_REASONS = {"error", "failed", "failure", "exception", "crash", "aborted",
                 "timeout", "cancelled", "canceled", "killed"}


def infer_status(*, ended_at: Optional[float], end_reason: Optional[str],
                 last_activity_at: Optional[float], message_count: int,
                 handoff_state: Optional[str] = None,
                 handoff_error: Optional[str] = None,
                 compression_failure_error: Optional[str] = None,
                 now: Optional[float] = None) -> SessionStatus:
    """Conservative status inference from Hermes session fields only.

    Order of checks (per the Hermes session-storage reference):
      1. error conditions first: handoff_state='failed', handoff_error set,
         or compression_failure_error set (more reliable than end_reason —
         real data has no generic 'error' end_reason).
      2. ended_at present  -> done
      3. otherwise open    -> working if activity within ACTIVE_WINDOW_SECONDS
      4. open + stale      -> idle
    WAITING is only emitted when the caller supplies an explicit signal
    (gateway routing suspended/resume_pending); never guessed from
    timestamps alone.
    """
    now = now if now is not None else time.time()

    if (handoff_state == "failed" or handoff_error or compression_failure_error):
        return SessionStatus.ERROR

    if ended_at is not None:
        return SessionStatus.DONE

    if last_activity_at is None:
        return SessionStatus.UNKNOWN

    age = now - last_activity_at
    if age <= ACTIVE_WINDOW_SECONDS and message_count > 0:
        return SessionStatus.WORKING
    return SessionStatus.IDLE


@dataclass
class Session:
    id: str
    source: str = ""
    agent: str = "main"            # resolved profile name (computed)
    profile: Optional[str] = None  # raw sessions.profile_name
    model: str = ""
    title: str = ""
    user_id: Optional[str] = None
    parent_session_id: Optional[str] = None
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    end_reason: Optional[str] = None
    handoff_state: Optional[str] = None
    handoff_error: Optional[str] = None
    compression_failure_error: Optional[str] = None
    last_activity_at: Optional[float] = None
    last_activity_description: Optional[str] = None
    message_count: int = 0
    tool_call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    estimated_cost_usd: Optional[float] = None
    chat_id: Optional[str] = None
    chat_type: Optional[str] = None
    thread_id: Optional[str] = None
    cwd: Optional[str] = None
    git_branch: Optional[str] = None
    git_repo_root: Optional[str] = None
    archived: bool = False
    hidden: bool = False
    pinned: bool = False
    origin_json: Optional[str] = None
    db: str = ""                   # which state.db this came from (for UI)
    status: SessionStatus = SessionStatus.UNKNOWN

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "source": self.source or "unknown",
            "agent": self.agent,
            "profile": self.profile,
            "model": self.model or "",
            "title": self.title or "",
            "status": self.status.value,
            "parent_session_id": self.parent_session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "end_reason": self.end_reason,
            "handoff_state": self.handoff_state,
            "handoff_error": self.handoff_error,
            "compression_failure_error": self.compression_failure_error,
            "last_activity_at": self.last_activity_at,
            "last_activity_description": self.last_activity_description,
            "message_count": self.message_count,
            "tool_call_count": self.tool_call_count,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "cache_read": self.cache_read_tokens,
                "cache_write": self.cache_write_tokens,
                "reasoning": self.reasoning_tokens,
                "total": (self.input_tokens + self.output_tokens
                          + self.cache_read_tokens + self.cache_write_tokens
                          + self.reasoning_tokens),
            },
            "estimated_cost_usd": self.estimated_cost_usd,
            "chat_id": self.chat_id,
            "chat_type": self.chat_type,
            "thread_id": self.thread_id,
            "cwd": self.cwd,
            "git_branch": self.git_branch,
            "archived": self.archived,
            "hidden": self.hidden,
            "pinned": self.pinned,
            "db": self.db,
        }
        return d


@dataclass
class Message:
    id: int
    session_id: str
    role: str
    content: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[str] = None   # raw JSON from Hermes
    tool_name: Optional[str] = None
    timestamp: Optional[float] = None
    token_count: Optional[int] = None
    finish_reason: Optional[str] = None
    reasoning: Optional[str] = None
    platform_message_id: Optional[str] = None
    active: bool = True
    compacted: bool = False
    display_kind: Optional[str] = None
    api_content: Optional[str] = None

    def to_dict(self, include_content: bool = True) -> dict:
        d = {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "timestamp": self.timestamp,
            "token_count": self.token_count,
            "finish_reason": self.finish_reason,
            "tool_call_id": self.tool_call_id,
            "tool_calls": _clip(self.tool_calls, MAX_TOOL_CALLS_CHARS),
            "tool_name": self.tool_name,
            "platform_message_id": self.platform_message_id,
            "active": self.active,
            "compacted": self.compacted,
            "display_kind": self.display_kind,
        }
        if include_content:
            d["content"] = _clip(self.content, MAX_CONTENT_CHARS)
            d["reasoning"] = _clip(self.reasoning, MAX_REASONING_CHARS)
        return d


@dataclass
class AgentInfo:
    name: str
    profile: Optional[str] = None
    models: list = field(default_factory=list)
    active_sessions: int = 0
    total_sessions: int = 0
    last_activity_at: Optional[float] = None
    last_activity_description: Optional[str] = None
    sources: list = field(default_factory=list)
    total_tool_calls: int = 0
    total_tokens: int = 0
    subagent_count: int = 0
