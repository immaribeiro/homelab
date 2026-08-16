"""Search tests: FTS trigram + metadata search + hostile input."""
from __future__ import annotations

import time

from backend.db import search_messages, search_sessions, _safe_fts_term
from backend.aggregate import Store


def _store(fake_home):
    from backend.db import discover_state_dbs, load_thread_profile_map
    dbs = discover_state_dbs(fake_home)
    st = Store(dbs, thread_map=load_thread_profile_map(fake_home / "config.yaml"))
    st.refresh()
    return st


def test_search_content_hits(fake_home):
    st = _store(fake_home)
    res = st.search("CVE-2026")
    assert any("CVE-2026" in (m.get("snippet") or "") for m in res["messages"])
    assert any(s.get("title") == "CVE-2026 research" for s in res["sessions"])


def test_search_agent_resolution(fake_home):
    st = _store(fake_home)
    res = st.search("kubectl")
    assert res["messages"]
    assert all(m["agent"] for m in res["messages"])


def test_search_empty_and_hostile_terms(fake_home):
    st = _store(fake_home)
    assert st.search("") == {"messages": [], "sessions": []}
    # FTS5 syntax-breaking input must not raise
    for hostile in ['"', '""', 'OR OR OR', "a' OR 1=1 --", "(", "NOT", "\\"]:
        res = st.search(hostile)
        assert isinstance(res, dict)
        assert "messages" in res and "sessions" in res


def test_safe_fts_term():
    assert _safe_fts_term('a "b" c') == '"a b c"'
    assert _safe_fts_term("   ") == ""
    assert _safe_fts_term("k3s") == '"k3s"'


def test_metadata_search(fake_home):
    st = _store(fake_home)
    res = st.search("Daily research")
    assert any(s.get("title") == "Daily research" for s in res["sessions"])


def test_trigram_search_messages(fake_home):
    """Search through the raw DB layer (trigram path or LIKE fallback)."""
    from backend.db import discover_state_dbs
    dbs = discover_state_dbs(fake_home)
    main = next(d for p, d in dbs if p == "main")
    hits = search_messages(("main", main), "CVE", limit=10)
    assert hits
    sess_hits = search_sessions(("main", main), "research", limit=10)
    assert any("CVE-2026 research" == s.get("title") for s in sess_hits)
