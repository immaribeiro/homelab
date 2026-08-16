"""Daily activity digest tests: sections, zero-state, secrets, read-only, CLI."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys

from backend.db import discover_state_dbs
from backend.digest import build_digest
from tests.conftest import ROOT

SECTION_HEADERS = ("Right now", "Agents", "Top models", "Sources",
                   "Notable sessions")


def test_digest_sections_present(fake_home, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(fake_home))
    out = build_digest(days=1)

    # Headline labels
    assert "Daily Activity Digest" in out
    assert "Sessions:" in out and "Messages:" in out and "Tool calls:" in out
    assert "Est. cost:" in out and "Active agents:" in out

    # Known agents and models appear
    for name in ("main", "engineer", "architect"):
        assert name in out, f"agent {name!r} missing from digest"
    for model in ("deepseek/deepseek-v4-flash", "gpt-5.6-luna",
                  "z-ai/glm-5.2"):
        assert model in out, f"model {model!r} missing from digest"

    # Every section is present with markdown bold markers
    for header in SECTION_HEADERS:
        assert header in out, f"section {header!r} missing"
    assert "**" in out


def test_digest_zero_sections_omitted(tmp_path, monkeypatch):
    """Empty home (no state.db at all) -> only the headline remains."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    out = build_digest(days=1)
    for header in SECTION_HEADERS:
        assert header not in out, f"section {header!r} should be omitted"
    # Headline-only (zeros) — never a crash, never stray sections.
    assert "Sessions: 0" in out
    assert "Messages: 0" in out


def test_digest_no_secrets(fake_home, monkeypatch):
    """origin_json / api_content values and field names never reach the digest."""
    monkeypatch.setenv("HERMES_HOME", str(fake_home))
    conn = sqlite3.connect(str(fake_home / "state.db"))
    conn.execute(
        "UPDATE sessions SET origin_json = ? WHERE id = 'cli_main'",
        (json.dumps({"OPENAI_API_KEY": "sk-secret123",
                     "TELEGRAM_BOT_TOKEN": "123:abc"}),))
    conn.execute(
        "INSERT INTO messages (session_id, role, content, api_content, timestamp) "
        "VALUES ('cli_main', 'assistant', 'digest must not show this', ?, 3.5)",
        (json.dumps({"OPENAI_API_KEY": "sk-secret456",
                     "TELEGRAM_BOT_TOKEN": "456:xyz"}),))
    conn.commit()
    conn.close()

    out = build_digest(days=1)
    for banned in ("origin_json", "api_content", "OPENAI_API_KEY",
                   "TELEGRAM_BOT_TOKEN", "sk-secret123", "sk-secret456",
                   "123:abc", "456:xyz", "digest must not show this"):
        assert banned not in out, f"{banned!r} leaked into the digest"


def test_digest_read_only(fake_home, monkeypatch):
    """build_digest never writes: every state.db byte is identical before/after."""
    monkeypatch.setenv("HERMES_HOME", str(fake_home))

    def snap():
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for _, p in discover_state_dbs(fake_home)}

    before = snap()
    build_digest(days=1)
    build_digest(days=7)
    after = snap()
    assert before == after


def test_digest_cli(fake_home, monkeypatch):
    """python -m backend.digest --days N prints Markdown digest to stdout."""
    env = os.environ.copy()
    env["HERMES_HOME"] = str(fake_home)
    env.pop("MISSION_CONTROL_TOKEN", None)
    r = subprocess.run(
        [sys.executable, "-m", "backend.digest", "--days", "1"],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "Daily Activity Digest" in r.stdout
    assert "**" in r.stdout and "Sessions:" in r.stdout
    # Telemetry never goes to stderr
    assert r.stderr.strip() == ""
