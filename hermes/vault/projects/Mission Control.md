---
created: 2026-08-18
updated: 2026-08-18
status: active
---

# 🛰️ Hermes Mission Control

Session observability dashboard for all Hermes profiles — what every agent is doing, session history, search, trends. Runs on the Mac Mini via launchd.

## Details

| Field | Value |
|-------|-------|
| **URL** | `http://imma-mini:9118` (tailnet; token auth, token at `~/.hermes/mission-control/token`) |
| **Repo** | `~/GitHub/homelab/mission-control/` (part of homelab repo) |
| **Stack** | FastAPI + stdlib sqlite3 (aggregates ALL profile state DBs: `~/.hermes/state.db` + `~/.hermes/profiles/*/state.db`) + vanilla-JS SPA (XSS-safe, dark theme, SSE live updates) |
| **Service** | launchd `ai.hermes.mission-control` (restart Python changes: `launchctl kickstart -k gui/501/ai.hermes.mission-control`; static files hot-reload) |
| **Design doc** | `mission-control/docs/architecture.md` + `hermes-observability` skill |

## Features

- Overview (status/source/agent counts), sessions list with agent/profile/source/model/status filters + search + trends
- **Status filter** incl. `hanging` (= idle + never ended — timed-out subagents), **sort** (last activity/started/messages/cost), **include-archived** toggle, pagination
- **Session management (2026-08-18):** archive/unarchive (`POST /api/sessions/{id}/archive`), delete with confirm + working/lease guard (`POST /api/sessions/{id}/delete`, requires `{"confirm": id}`), export (JSON/MD), copy-ID — all same-origin + auth protected
- Hanging quick-chip, toasts, refresh, SSE live updates

## Notes

- Read paths open state.db `mode=ro`; the only writes are the two narrow per-session helpers (archive flag / delete session+messages) — deliberately minimal
- Bulk CLI (`hermes sessions archive`) can't reach child/shared sessions; the UI's per-session endpoints can (used to clean the dangling reader-subagent session)

## Related

- [[Homelab Infrastructure]] — where this runs
- [[Hermes Multi-Agent System]] — the agents it observes
