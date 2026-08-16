"""Daily activity digest — Telegram-safe Markdown summary of Hermes usage.

Pure read-only aggregation on top of the existing Store (backend/aggregate.py):
no direct DB access here. Every section build is wrapped in try/except so
build_digest never crashes — a failing section degrades to being omitted.

Output rules (architect-approved): plain Markdown with ** bold, short lines,
no HTML, no tables, minimal/no emoji, ISO local dates, cost at 2 decimals,
token counts as k/M.
"""
from __future__ import annotations

import argparse
import time
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Optional

from .aggregate import Store
from .db import default_hermes_home, discover_state_dbs, load_thread_profile_map

MAX_DAYS = 90


def _fmt_cost(value) -> str:
    try:
        return f"${float(value or 0):.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _fmt_tokens(n) -> str:
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _clean(text: Optional[str]) -> str:
    """Collapse whitespace/newlines so a title can't break the Markdown layout."""
    return " ".join((text or "").split())


def _session_tokens(s) -> int:
    return (s.input_tokens + s.output_tokens + s.cache_read_tokens
            + s.cache_write_tokens + s.reasoning_tokens)


def _load_store() -> Store:
    """Fresh Store over every state.db under HERMES_HOME (same discovery as db.py)."""
    dbs = discover_state_dbs()
    store = Store(dbs, thread_map=load_thread_profile_map())
    store.refresh()
    return store


# ── section builders (each returns lines or None to skip) ──────────────

def _build_headline(sessions: list, days: int, now: float) -> Optional[str]:
    if sessions is None:
        return None
    start = datetime.fromtimestamp(now - (days - 1) * 86400).strftime("%Y-%m-%d")
    end = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
    n_sessions = len(sessions)
    n_msgs = sum(s.message_count or 0 for s in sessions)
    n_tools = sum(s.tool_call_count or 0 for s in sessions)
    cost = sum(s.estimated_cost_usd or 0.0 for s in sessions)
    agents = sorted({s.agent for s in sessions})
    return "\n".join([
        "**Daily Activity Digest**",
        f"{start} to {end}",
        "",
        f"Sessions: {n_sessions} | Messages: {n_msgs} | Tool calls: {n_tools}",
        f"Est. cost: {_fmt_cost(cost)} | Active agents: {len(agents)}",
    ])


def _build_right_now(store: Store) -> Optional[str]:
    ov = store.overview()
    sc = ov.get("status_counts") or {}
    working = sc.get("working", 0)
    waiting = sc.get("waiting", 0)
    idle = sc.get("idle", 0)
    if working == 0 and waiting == 0 and idle == 0:
        return None
    lines = ["**Right now**",
             f"Working: {working} | Waiting: {waiting} | Idle: {idle}"]
    working_agents = [a["name"] for a in (ov.get("agents") or [])
                      if a.get("active_sessions", 0) > 0]
    if working_agents:
        lines.append("Working: " + ", ".join(sorted(working_agents)))
    return "\n".join(lines)


def _build_agents(sessions: list) -> Optional[str]:
    by_agent = defaultdict(list)
    for s in sessions:
        by_agent[s.agent].append(s)
    if not by_agent:
        return None
    lines = ["**Agents**"]
    for name in sorted(by_agent):
        ss = by_agent[name]
        models = sorted({s.model for s in ss if s.model})
        tools = sum(s.tool_call_count or 0 for s in ss)
        cost = sum(s.estimated_cost_usd or 0.0 for s in ss)
        lines.append(
            f"{name} — {len(ss)} sessions, {tools} tool calls, "
            f"models: {', '.join(models)}, est {_fmt_cost(cost)}"
        )
    return "\n".join(lines)


def _build_top_models(sessions: list) -> Optional[str]:
    stats = defaultdict(lambda: {"tokens": 0, "cost": 0.0})
    for s in sessions:
        name = s.model or "unknown"
        stats[name]["tokens"] += _session_tokens(s)
        stats[name]["cost"] += s.estimated_cost_usd or 0.0
    ranked = [kv for kv in sorted(stats.items(), key=lambda kv: -kv[1]["tokens"])
              if kv[1]["tokens"] > 0][:5]
    if not ranked:
        return None
    lines = ["**Top models**"]
    for name, st in ranked:
        lines.append(f"{name} — {_fmt_tokens(st['tokens'])} tokens, "
                     f"{_fmt_cost(st['cost'])}")
    return "\n".join(lines)


def _build_sources(sessions: list) -> Optional[str]:
    counts = Counter(s.source or "unknown" for s in sessions)
    if not counts:
        return None
    lines = ["**Sources**"]
    lines += [f"{name}: {n} sessions" for name, n in counts.most_common()]
    return "\n".join(lines)


def _build_notable(sessions: list) -> Optional[str]:
    if not sessions:
        return None
    longest = max(sessions, key=lambda s: s.message_count or 0)
    most_tools = max(sessions, key=lambda s: s.tool_call_count or 0)
    errors = [s for s in sessions
              if s.handoff_state == "failed" or s.handoff_error
              or s.compression_failure_error]
    entries: List[tuple] = []
    seen = set()
    for candidate, label in ((longest, "longest"),
                             (most_tools, "most tool calls")):
        if candidate.id in seen:
            continue
        seen.add(candidate.id)
        detail = (f"({candidate.message_count} msgs)" if label == "longest"
                  else f"({candidate.tool_call_count} tool calls)")
        entries.append((label, candidate, detail))
    for s in sorted(errors, key=lambda x: x.started_at or 0, reverse=True):
        if s.id in seen:
            continue
        seen.add(s.id)
        entries.append(("error", s, "(error)"))
        if len(entries) >= 5:
            break
    if not entries:
        return None
    lines = ["**Notable sessions**"]
    for label, s, detail in entries[:5]:
        title = _clean(s.title) or "(untitled)"
        lines.append(f"{label}: {s.id} ({s.agent}) — {title} {detail}")
    return "\n".join(lines)


# ── public API ─────────────────────────────────────────────────────────

def build_digest(days: int = 1) -> str:
    """Return the daily activity digest as Telegram-safe Markdown.

    Covers sessions started within the last `days` days (local time).
    Never raises: every section degrades to being omitted on failure.
    """
    try:
        days = max(1, min(int(days), MAX_DAYS))
    except (TypeError, ValueError):
        days = 1
    now = time.time()
    cutoff = now - days * 86400

    try:
        store = _load_store()
    except Exception:  # noqa: BLE001 — digest must never crash
        store = None

    try:
        all_sessions = store.sessions if store is not None else []
        sessions = [s for s in all_sessions if (s.started_at or 0) >= cutoff]
    except Exception:  # noqa: BLE001
        sessions = []

    builders = [
        ("headline", lambda: _build_headline(sessions, days, now)),
        ("right_now", lambda: _build_right_now(store) if store else None),
        ("agents", lambda: _build_agents(sessions)),
        ("top_models", lambda: _build_top_models(sessions)),
        ("sources", lambda: _build_sources(sessions)),
        ("notable", lambda: _build_notable(sessions)),
    ]
    sections = []
    for _name, builder in builders:
        try:
            section = builder()
        except Exception:  # noqa: BLE001 — degrade to an empty section
            section = None
        if section:
            sections.append(section)

    if not sections:
        return ""
    return "\n\n".join(sections) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print the daily Hermes activity digest as Telegram-safe Markdown.")
    parser.add_argument("--days", type=int, default=1,
                        help="Days of history to cover (default: 1)")
    args = parser.parse_args()
    print(build_digest(days=args.days), end="")
