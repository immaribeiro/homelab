"""Authentication for Hermes Mission Control.

Model (fail-closed by default):
- A single bearer token gates the whole app when authentication is enabled.
- If the service binds to a non-loopback address, the token is MANDATORY and
  the service refuses to start without it.
- If bound to loopback, the token is optional: when absent, local access is
  open (convenience for a personal machine); when present, it is enforced.
- Sessions use an HttpOnly, SameSite=Strict cookie after login; API clients
  may also send `X-Auth-Token`.

The token itself lives in MISSION_CONTROL_TOKEN (env) or is auto-generated on
first run and stored in a 0600 file under the data dir. It is never logged.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path
from typing import Optional


def _is_loopback(host: str) -> bool:
    return host in ("127.0.0.1", "::1", "localhost", "")


def load_or_create_token(data_dir: Path, force: bool = False) -> str:
    """Return the configured token.

    - MISSION_CONTROL_TOKEN env var always wins.
    - An existing token file is reused.
    - Otherwise a token is generated and persisted ONLY when `force` is set
      (i.e. when binding a non-loopback address); loopback binds stay open.
    """
    env = os.environ.get("MISSION_CONTROL_TOKEN", "").strip()
    if env:
        return env
    data_dir.mkdir(parents=True, exist_ok=True)
    token_file = data_dir / "token"
    if token_file.exists():
        tok = token_file.read_text(encoding="utf-8").strip()
        if tok:
            return tok
    if not force:
        return ""
    tok = secrets.token_urlsafe(32)
    token_file.write_text(tok + "\n", encoding="utf-8")
    try:
        token_file.chmod(0o600)
    except OSError:
        pass
    return tok


def auth_enabled(host: str, token: Optional[str]) -> bool:
    """Authentication is enforced when a token is configured or when the
    service is reachable beyond loopback (fail closed)."""
    if token:
        return True
    return not _is_loopback(host)


def token_matches(token: Optional[str], expected: str) -> bool:
    if not token:
        return False
    return hmac.compare_digest(token, expected)


def make_session_cookie() -> str:
    """Opaque session cookie value (random; server is stateless, the value
    simply proves the bearer token was presented at login time)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """For any audit/diagnostic use: never store or log raw tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
