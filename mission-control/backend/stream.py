"""Server-Sent Events stream for live dashboard updates.

Cheap change detection: every POLL_SECONDS the aggregator reloads its
snapshot and compares a fingerprint (max last_activity_at + counts + DB
mtimes). Only when it changes do we emit an event containing the compact
overview payload. Heartbeat comments keep proxies from timing the
connection out.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import List, Optional, Tuple

POLL_SECONDS = 4
HEARTBEAT_SECONDS = 15


def _db_fingerprint(dbs: List[Tuple[str, Path]], store) -> str:
    parts = []
    for _profile, path in dbs:
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0
        parts.append(f"{path.name}:{mtime:.1f}")
    sessions = store.sessions
    max_act = max((s.last_activity_at or 0) for s in sessions) if sessions else 0
    parts.append(f"max:{max_act:.1f}")
    parts.append(f"n:{len(sessions)}")
    parts.append(f"msgs:{sum(s.message_count for s in sessions)}")
    return "|".join(parts)


async def event_stream(store, dbs: List[Tuple[str, Path]]):
    """Async generator yielding SSE frames."""
    last_fp: Optional[str] = None
    last_heartbeat: float = 0.0

    while True:
        started = time.monotonic()
        try:
            store.refresh()
            fp = _db_fingerprint(dbs, store)
            if fp != last_fp:
                last_fp = fp
                payload = json.dumps(store.overview())
                yield f"event: refresh\ndata: {payload}\n\n"
                last_heartbeat = time.monotonic()
        except Exception as exc:  # noqa: BLE001 — keep the stream alive
            yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
            last_heartbeat = time.monotonic()

        elapsed = time.monotonic() - started
        sleep_for = max(0.5, POLL_SECONDS - elapsed)
        await asyncio.sleep(sleep_for)

        if time.monotonic() - last_heartbeat >= HEARTBEAT_SECONDS:
            yield ": heartbeat\n\n"
            last_heartbeat = time.monotonic()
