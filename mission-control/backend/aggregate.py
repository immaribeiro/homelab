"""Aggregation across all Hermes profile state databases."""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .db import (load_child_sessions, load_gateway_routing, load_session,
                 load_sessions, load_turn_leases, resolve_agent,
                 search_messages, search_sessions)
from .models import AgentInfo, Message, Session, SessionStatus


class Store:
    """Read-only facade over every Hermes state.db.

    Loads each database once per refresh cycle; callers get a consistent
    snapshot for the duration of a request.
    """

    def __init__(self, dbs: List[Tuple[str, Path]],
                 thread_map: Optional[Dict[str, str]] = None,
                 telegram_titles: Optional[List[str]] = None):
        self.dbs = dbs                      # [(profile, path)]
        self.thread_map = thread_map or {}
        self.telegram_titles = telegram_titles or [
            "Main", "Architect", "Backend", "Frontend", "Engineer",
        ]
        self._sessions: List[Session] = []
        self._by_id: Dict[str, Session] = {}
        self._by_db: Dict[str, List[Session]] = defaultdict(list)
        self._loaded_at: float = 0.0
        self._errors: List[str] = []

    # ── loading ──────────────────────────────────────────────────────────
    def refresh(self, now: Optional[float] = None) -> None:
        """(Re)load every session from every DB, resolving agents."""
        now = now if now is not None else time.time()
        self._sessions = []
        self._by_id = {}
        self._by_db = defaultdict(list)
        self._errors = []

        for profile, path in self.dbs:
            try:
                sess = load_sessions((profile, path), now=now)
            except Exception as exc:  # noqa: BLE001 — isolate a bad DB
                self._errors.append(f"{profile}: {exc}")
                continue
            for s in sess:
                s.agent = resolve_agent(s, self.thread_map, self.telegram_titles)
                self._sessions.append(s)
                self._by_id[s.id] = s
                self._by_db[profile].append(s)

        # Authoritative activity overrides from gateway state (turn leases
        # and per-channel routing). A live turn lease means the gateway is
        # running that session's turn right now.
        leases: Dict[str, tuple] = {}
        routing: Dict[str, dict] = {}
        for profile, path in self.dbs:
            leases.update(load_turn_leases((profile, path)))
            routing.update(load_gateway_routing((profile, path)))
        for s in self._sessions:
            lease = leases.get(s.id)
            if lease and lease[1] > now and lease[0] <= now + 60:
                s.status = SessionStatus.WORKING
                continue
            route = routing.get(s.id)
            if route:
                # Gateway turn token set durably -> the gateway is mid-turn.
                if route.get("active_turn_token") and route.get("active_turn_started_at"):
                    s.status = SessionStatus.WORKING
                    continue
                # Suspended / resume pending -> waiting for user input.
                if route["suspended"] or route["resume_pending"]:
                    if s.status != SessionStatus.DONE:
                        s.status = SessionStatus.WAITING

        self._loaded_at = now

    @property
    def sessions(self) -> List[Session]:
        return self._sessions

    @property
    def errors(self) -> List[str]:
        return self._errors

    def get(self, session_id: str) -> Optional[Tuple[Session, Tuple[str, Path]]]:
        """Session plus the DB tuple needed to fetch its messages."""
        s = self._by_id.get(session_id)
        if s is None:
            return None
        db = next((d for d in self.dbs if d[0] == s.db), None)
        return (s, db) if db else None

    def messages(self, session_id: str) -> List[Message]:
        pair = self.get(session_id)
        if not pair:
            return []
        from .db import load_messages
        return load_messages(pair[1], session_id)

    def children(self, session_id: str) -> List[Session]:
        pair = self.get(session_id)
        if not pair:
            return []
        kids = load_child_sessions(pair[1], session_id)
        for k in kids:
            k.agent = resolve_agent(k, self.thread_map, self.telegram_titles)
        return kids

    def search(self, term: str, limit: int = 50) -> dict:
        """Global search across message content + session metadata."""
        term = (term or "").strip()
        if not term:
            return {"messages": [], "sessions": []}
        msgs, sess = [], []
        for profile, path in self.dbs:
            try:
                msgs.extend(search_messages((profile, path), term, limit))
                sess.extend(search_sessions((profile, path), term, limit))
            except Exception:  # noqa: BLE001
                continue
        # Resolve agent for message hits via their session id
        by_id = self._by_id
        for m in msgs:
            owner = by_id.get(m.get("session_id"))
            m["agent"] = owner.agent if owner else "main"
        # Attach agent to session hits
        for s in sess:
            owner = by_id.get(s.get("id"))
            s["agent"] = owner.agent if owner else "main"
        msgs.sort(key=lambda m: m.get("timestamp") or 0, reverse=True)
        sess.sort(key=lambda s: s.get("started_at") or 0, reverse=True)
        return {"messages": msgs[:limit], "sessions": sess[:limit]}

    # ── views ────────────────────────────────────────────────────────────
    def overview(self, now: Optional[float] = None) -> dict:
        now = now if now is not None else time.time()
        sessions = self._sessions
        by_agent: Dict[str, List[Session]] = defaultdict(list)
        status_counts = Counter(s.status.value for s in sessions)
        source_counts = Counter(s.source for s in sessions)
        total_tools = sum(s.tool_call_count for s in sessions)
        total_msgs = sum(s.message_count for s in sessions)

        for s in sessions:
            by_agent[s.agent].append(s)

        # Agents with their current state
        agents = []
        for name, ss in sorted(by_agent.items()):
            active = [s for s in ss if s.status == SessionStatus.WORKING]
            last = max((s.last_activity_at or 0) for s in ss) or None
            last_desc = None
            for s in sorted(ss, key=lambda x: x.last_activity_at or 0, reverse=True):
                if s.last_activity_description:
                    last_desc = s.last_activity_description
                    break
            models = sorted({s.model for s in ss if s.model})
            sources = sorted({s.source for s in ss})
            agents.append(AgentInfo(
                name=name,
                models=models,
                active_sessions=len(active),
                total_sessions=len(ss),
                last_activity_at=last,
                last_activity_description=last_desc,
                sources=sources,
                total_tool_calls=sum(s.tool_call_count for s in ss),
                total_tokens=sum(
                    s.input_tokens + s.output_tokens + s.cache_read_tokens
                    + s.cache_write_tokens + s.reasoning_tokens for s in ss),
                subagent_count=sum(1 for s in ss if s.parent_session_id),
            ))

        agents.sort(key=lambda a: a.last_activity_at or 0, reverse=True)

        # Model usage rollup (tokens + cost per model)
        model_stats: Dict[str, dict] = {}
        for s in sessions:
            name = s.model or "unknown"
            ms = model_stats.setdefault(name, {
                "model": name, "sessions": 0, "messages": 0,
                "tool_calls": 0, "tokens": 0, "estimated_cost_usd": 0.0,
            })
            ms["sessions"] += 1
            ms["messages"] += s.message_count
            ms["tool_calls"] += s.tool_call_count
            ms["tokens"] += (s.input_tokens + s.output_tokens
                             + s.cache_read_tokens + s.cache_write_tokens
                             + s.reasoning_tokens)
            if s.estimated_cost_usd:
                ms["estimated_cost_usd"] += s.estimated_cost_usd
        model_stats = sorted(model_stats.values(), key=lambda x: -x["tokens"])[:10]
        model_stats = list(model_stats)  # type: ignore[assignment]

        # Recent activity feed (last N sessions by activity)
        recent = sorted(
            sessions,
            key=lambda s: s.last_activity_at or s.started_at or 0,
            reverse=True,
        )[:25]

        return {
            "stats": {
                "agents": len(agents),
                "active_sessions": status_counts.get("working", 0),
                "sessions": len(sessions),
                "tool_calls": total_tools,
                "messages": total_msgs,
                "open_sessions": sum(1 for s in sessions if s.ended_at is None),
            },
            "status_counts": dict(status_counts),
            "source_counts": dict(source_counts),
            "model_stats": model_stats,
            "agents": [a.__dict__ for a in agents],
            "recent_activity": [s.to_dict() for s in recent],
            "db_errors": self._errors,
            "loaded_at": self._loaded_at,
        }

    def agents(self, now: Optional[float] = None) -> List[dict]:
        return self.overview(now)["agents"]

    def sources(self) -> List[dict]:
        counts = Counter(s.source for s in self._sessions)
        return [{"source": k, "count": v} for k, v in sorted(
            counts.items(), key=lambda kv: -kv[1])]
