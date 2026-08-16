---
created: 2026-08-16
updated: 2026-08-16
tags: [hermes, dashboard, observability, sessions]
---

# 🎛 Hermes Mission Control

Read-only observability dashboard for **all** Hermes agents, sessions, and
sources — Telegram, CLI, desktop, cron, everything.

**URL (Mac Mini):** http://127.0.0.1:9118 (loopback only — see Remote access)

## What it answers

> What are ALL my Hermes agents doing right now, what sessions do they have,
> where did those sessions come from, and what have they been doing?

- **Overview** — agents, working/active counts, sessions, tool calls, status
  distribution, recent activity feed (live via SSE)
- **Sessions** — filterable table (agent / source / model / status / date /
  search); Telegram sessions attributed to their agent via forum thread →
  profile mapping
- **Session detail** — full conversation, expandable tool calls (args),
  metadata, subagent children
- **Agents** — per-agent cards: models, active/total sessions, tool usage,
  tokens, subagents → drill into that agent's sessions
- **Search** — full-text across all conversation content (FTS5 trigram)

## Status semantics (from real Hermes state)

| Status | Source |
|---|---|
| 🟢 working | live `session_turn_leases` entry (gateway running that turn) |
| 🟡 waiting | `gateway_routing` `suspended`/`resume_pending` |
| 🔵 idle / ⚪ done / 🔴 error | recency / `ended_at` + `end_reason` |

## Architecture

```
~/.hermes/state.db + profiles/*/state.db  ──(read-only mode=ro)──►  FastAPI :9118
                                                                        │
                                  REST /api/overview, /api/sessions,    │
                                  /api/search, /api/agents …  + SSE ───┤
                                                                        ▼
                                              static/ vanilla JS SPA (dark)
```

- **Source of truth:** the SQLite `sessions`/`messages` tables in each
  profile's `state.db`. Multiplexed Telegram sessions live in the **main**
  state.db with `thread_id`; `config.yaml` `gateway.profile_routes` maps
  thread → agent. `~/.hermes/sessions/*.jsonl` are transcripts, not canonical.
- **Never writes:** every connection is `mode=ro`; the gateway and agents are
  untouched.

## Code

- Repo: `~/GitHub/homelab/mission-control/`
- Docs: `README.md`, `docs/architecture.md`
- Tests: `venv/bin/python -m pytest tests/` (31 passing)
- Service: launchd `ai.hermes.mission-control` (plist in `deploy/`), logs in
  `~/.hermes/logs/mission-control.{log,error.log}`

## Remote access (private only)

```bash
tailscale serve --bg 9118        # tailnet-only HTTPS
# or: ssh -L 9118:127.0.0.1:9118 imma-mini
```

Never expose publicly — it shows private conversations. The Hermes dashboard
(9119, hermes.immas.org) is the public surface with Nous OAuth.

## Related

- [[Public Dashboard Access]] — the 9119 dashboard (public, OAuth)
- [[Hermes Config]]
- [[Agent Overview]]
