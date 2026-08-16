# Hermes Mission Control

A read-only **observability dashboard** for a multi-agent Hermes installation.
One URL answers the question: *"What are ALL my Hermes agents doing right now,
what sessions do they have, where did those sessions come from, and what have
they been doing?"*

It aggregates sessions from **every Hermes profile** (main + architect,
backend, frontend, engineer, …) and **every source** (Telegram, CLI, desktop,
cron, …) into a single dark-theme Mission Control UI.

```
Hermes state.db (main + profiles/*/state.db)   ← read-only (mode=ro)
        │
        ▼
Mission Control backend (FastAPI, port 9118)
        │
        ├── REST API  (/api/overview, /api/sessions, /api/search, …)
        └── SSE stream (/api/stream — live updates every ~4s)
        │
        ▼
Mission Control UI (vanilla JS SPA, dark theme)
```

**It never writes to Hermes state. It never touches the gateway.** The
Telegram gateway, agents, and existing dashboard keep working exactly as
before.

---

## Quick start

```bash
cd ~/GitHub/homelab/mission-control

# Run in the foreground (dev):
/Users/imma/.hermes/hermes-agent/venv/bin/python -m backend.run
# → http://127.0.0.1:9118

# Install as a launchd service (macOS, auto-start + auto-restart):
cp deploy/ai.hermes.mission-control.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/ai.hermes.mission-control.plist

# Stop / uninstall:
launchctl unload ~/Library/LaunchAgents/ai.hermes.mission-control.plist
```

## Tests

```bash
cd ~/GitHub/homelab/mission-control
/Users/imma/.hermes/hermes-agent/venv/bin/python -m pytest tests/ -q
```

Covers: session discovery, Telegram attribution, status inference (turn
leases), filters, FTS search + hostile input, API shapes, auth (fail-closed),
read-only enforcement, SQL injection attempts, secret leakage.

## Configuration

All via environment variables (see the launchd plist):

| Env var | Default | Meaning |
|---|---|---|
| `MISSION_CONTROL_HOST` | `127.0.0.1` | Bind address. **Keep loopback.** |
| `MISSION_CONTROL_PORT` | `9118` | Listen port. |
| `MISSION_CONTROL_TOKEN` | auto | Access token (only needed for non-loopback). |
| `MISSION_CONTROL_DATA_DIR` | `~/.hermes/mission-control` | Where the auto-generated token file lives. |
| `HERMES_HOME` | `~/.hermes` | Hermes home (state DB discovery root). |

Auth model (fail-closed):
- **Loopback bind, no token** → open (convenient for a personal machine).
- **Loopback bind, token set** → login required.
- **Non-loopback bind** → token **required**; the service refuses to start
  without one (a token is auto-generated into `MISSION_CONTROL_DATA_DIR/token`,
  chmod 600).

## API

| Endpoint | Description |
|---|---|
| `GET /api/health` | Liveness (no auth). |
| `GET /api/config` | Public settings (no secrets). |
| `GET /api/overview` | Stats, status/source distribution, agents, recent activity. |
| `GET /api/sessions` | Filterable list: `agent, profile, source, model, status, q, date_from, date_to, active, limit, offset`. |
| `GET /api/sessions/{id}` | Detail: metadata + conversation + tool calls + subagent children. |
| `GET /api/agents` | Per-agent rollups (models, active/total sessions, tool usage, tokens). |
| `GET /api/sources` | Source distribution. |
| `GET /api/search?q=` | Global FTS search (message content + session metadata). |
| `GET /api/stream` | SSE live updates (refresh events with compact overview). |
| `POST /api/login` | `{"token": "…"}` → sets the session cookie. |

## Status semantics

Derived conservatively from Hermes data — no invented states:

| Status | Signal |
|---|---|
| 🟢 **working** | Live turn lease in `session_turn_leases` (gateway is running that session's turn right now), or open session with activity < 2 min. |
| 🟡 **waiting** | `gateway_routing` entry flagged `suspended` / `resume_pending`. |
| 🔵 **idle** | Open session, no lease, no recent activity. |
| ⚪ **done** | `ended_at` set (normal `end_reason`). |
| 🔴 **error** | `ended_at` set with an error-ish `end_reason`. |
| ⚫ **unknown** | No activity timestamps at all. |

## Agent attribution

A session's agent (profile) is resolved in priority order:

1. `sessions.profile_name` (set when a profile runs its own session)
2. Telegram forum topic: `thread_id` → profile from `gateway.profile_routes`
   in `config.yaml` (multiplexed Telegram sessions live in the **main**
   state.db with `thread_id` set; the map attributes them; `default` is
   normalized to `main`)
3. Telegram session titled with an agent name (`Main`, `Architect`, …)
4. `main`

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full discovery
report (Hermes state schema, `state.db` vs `sessions/` transcripts, the
official dashboard's per-profile API, and why this layer exists).

- `backend/db.py` — read-only SQLite access + discovery + FTS search
- `backend/models.py` — session/message models + status inference
- `backend/aggregate.py` — cross-DB merge, agent resolution, overview/agents
- `backend/api.py` — FastAPI app + auth
- `backend/stream.py` — SSE change-detection stream
- `static/` — the SPA (vanilla JS; **all** dynamic data rendered via
  `textContent`, never `innerHTML`)

## Security

- **Read-only by construction**: every SQLite connection uses `mode=ro`;
  write statements are impossible (tests assert this).
- **Loopback by default**; token auth is fail-closed for any non-loopback bind.
- **No secrets**: the API never serializes `.env` contents, tokens, or
  credentials; `origin_json`/`api_content` are intentionally not exposed.
- **XSS-safe UI**: no `innerHTML` with data; HTML-unsafe content is rendered
  as text.
- **SQL injection**: all queries parameterized; FTS terms are quoted phrases.
- Session cookie: `HttpOnly` + `SameSite=Strict`.

## Remote access (private network only — never public)

The service is designed to stay on the Mac Mini's loopback. To reach it from
your MacBook / iPhone over your private network:

**Option A — Tailscale Serve (recommended).** Expose it on your tailnet only:

```bash
tailscale serve --bg 9118        # then open http://imma-mini:9118 from any tailnet device
```

Optionally add a token (`MISSION_CONTROL_TOKEN=…` in the plist) so the tailnet
login page is required.

**Option B — SSH tunnel.** From the MacBook/iPhone:

```bash
ssh -L 9118:127.0.0.1:9118 imma-mini
# then open http://127.0.0.1:9118 locally
```

> **Do not** expose it to the public internet. It shows private AI
> conversations and tool calls. The Hermes dashboard (9119) is already public
> via Cloudflare Tunnel with Nous OAuth — Mission Control deliberately is not.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Nothing on :9118 | `launchctl list \| grep mission`; check `~/.hermes/logs/mission-control.error.log`. |
| No sessions shown | Check `HERMES_HOME` in the plist; `GET /api/health` reports `dbs` count. |
| "DB errors" in the footer | One state.db failed to open (corrupt/locked); the others still load. |
| Auth required but no token | Non-loopback bind without token → set `MISSION_CONTROL_TOKEN` or read the auto-generated one from `MISSION_CONTROL_DATA_DIR/token`. |
| Live pill never turns green | SSE blocked (proxy); the UI still refreshes on navigation. |

## Validation checklist

- [x] All Hermes sessions discovered (main + every profile state.db)
- [x] Telegram sessions appear (incl. forum-topic attribution to agents)
- [x] CLI / desktop / cron sessions appear
- [x] Agents + profiles identified
- [x] Session detail: conversation, tool calls (args), metadata, timeline
- [x] Global search (FTS) + filters (agent/source/model/status/date)
- [x] Agent view + source filtering
- [x] Live updates via SSE (status from turn leases)
- [x] Subagent relationships (parent → children)
- [x] No Hermes data modified (read-only connections, tested)
- [x] No credentials exposed (tested)
- [x] Authentication fail-closed for remote binds (tested)
- [x] Remote access private by default (loopback bind)
- [x] Existing gateway + agents untouched (no config/process changes)
- [x] Automated tests pass (30 tests)
