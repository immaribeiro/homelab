# Hermes Mission Control — Architecture & Discovery Report

## 1. Existing Hermes environment (discovered)

| Fact | Value |
|---|---|
| Hermes version | v0.20.1 (2026.8.13), install dir `~/.hermes/hermes-agent` |
| Gateway | launchd `ai.hermes.gateway`, `multiplex_profiles: true`, Telegram connected |
| Dashboard | launchd `ai.hermes.dashboard` on `:9119` (0.0.0.0, basic + Nous OAuth) |
| Profiles | main (`~/.hermes`) + architect, backend, frontend, engineer (`~/.hermes/profiles/<n>/`) |
| Session store | SQLite per profile: `~/.hermes/state.db` + `profiles/*/state.db` (WAL mode) |
| Transcripts | `~/.hermes/sessions/*.jsonl` — export/transcript files, **not** the canonical store |
| Sources observed | `cli`, `telegram`, `desktop`, `cron`, `unknown` |

### Where Telegram sessions live

Multiplexed Telegram sessions (forum topics → profiles) are written **centrally
into the main profile's `state.db`** by the gateway, with `thread_id` set and
`profile_name` NULL. Titles follow the routed agent (`Main`, `Engineer`, …).
Per-profile DBs only hold sessions a profile ran itself (e.g. `architect chat`).

This is why Hermes Desktop's per-profile views feel incomplete: Telegram
sessions are in the main DB, not the profile DBs, and the official dashboard
reads one profile at a time.

## 2. `state.db` schema (canonical source of truth)

### `sessions`

```sql
id TEXT PRIMARY KEY,            -- e.g. 20260816_182124_0ff7b89f
source TEXT NOT NULL,           -- cli | telegram | desktop | cron | unknown | ...
user_id, model, model_config,
parent_session_id,              -- FK → sessions.id  (subagent relationship)
started_at REAL, ended_at REAL, end_reason,
message_count, tool_call_count,
input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens,
estimated_cost_usd, actual_cost_usd, cost_status,
title, cwd, chat_id, chat_type, thread_id,     -- Telegram origin (thread = forum topic)
git_branch, git_repo_root,
archived, hidden, pinned, profile_name,        -- profile_name NULL in main DB
origin_json, session_key, display_name,
last_activity_at REAL, last_activity_description, last_activity_provenance,
handoff_state, handoff_platform
```

### `messages`

```sql
id INTEGER PK, session_id FK, role,            -- user | assistant | tool | system | ...
content, tool_call_id, tool_calls TEXT(JSON),  -- args of assistant tool calls
tool_name, timestamp REAL, token_count, finish_reason,
reasoning, reasoning_content, platform_message_id,
active, compacted, display_kind, api_content
```

### Supporting tables

- `messages_fts` / `messages_fts_trigram` — FTS5 (incl. trigram) full-text
  index over content + tool_name + tool_calls, kept in sync by triggers.
- `session_turn_leases` — `(conversation_id, holder, acquired_at, expires_at)`.
  **A live lease = the gateway is running that session's turn right now** — the
  authoritative "working" signal.
- `gateway_routing` — per-channel state JSON: `session_id`, `suspended`,
  `resume_pending`, `active_turn_token`, `origin` (platform/chat/thread/user).
  `suspended`/`resume_pending` → "waiting for input".
- `session_model_usage`, `system_prompts`, `async_delegations`,
  `delivery_obligations`, `state_meta`, `schema_version`.

### `sessions.json`?

There is no `sessions.json`. The `sessions/` directory holds `.jsonl`
transcripts (8) and `request_dump_*.json` artifacts (48). `state.db` is the
canonical session history; Mission Control reads it directly.

## 3. Why not extend the official dashboard?

The official dashboard (`hermes dashboard`) is a full React app with a
per-profile REST API (`/api/sessions`, `/api/sessions/search`) that reads the
**selected profile's** DB. It does not aggregate across profiles, has no
agent-centric view, no live activity feed, no subagent tree, and no
source-first filtering. Forking a React app with an npm build to add a
cross-profile observability layer is heavier and riskier than a focused,
read-only, dependency-light layer — which also matches Hermes's own guidance
that observability tooling ships as a standalone app, not in the core tree.

## 4. Mission Control architecture

```
~/.hermes/state.db  +  ~/.hermes/profiles/*/state.db
        │  (sqlite3 URI mode=ro — writes are impossible)
        ▼
backend/db.py          discovery, read-only queries, FTS search,
                       thread→profile map (from config.yaml)
backend/models.py      Session/Message models, status inference
backend/aggregate.py   cross-DB merge, agent resolution, overview/agents
backend/api.py         FastAPI: REST + auth + static SPA
backend/stream.py      SSE change detection (poll ~4s, push on change)
        │
        ▼
static/                vanilla JS SPA (no build step) — Overview,
                       Sessions, Session detail, Agents, Search
```

### Agent (profile) resolution

1. `sessions.profile_name`
2. Telegram `thread_id` → `gateway.profile_routes` from `config.yaml`
   (`default` normalized to `main`)
3. Telegram title heuristic (multiplexer titles sessions after the agent)
4. `main`

### Status inference (conservative)

1. Live turn lease → **working**
2. `gateway_routing.suspended`/`resume_pending` → **waiting**
3. `ended_at` → **done** (or **error** by `end_reason`)
4. Open + activity < 2 min → **working**; else → **idle**; no timestamps →
   **unknown**

## 5. Security model

- **Read-only**: every connection `mode=ro`; tests assert writes fail.
- **Loopback by default**; token auth fail-closed for non-loopback binds
  (auto-generated token, chmod 600, or `MISSION_CONTROL_TOKEN`).
- **Cookie** `mc_session`: HttpOnly, SameSite=Strict, stateless.
- **XSS**: UI renders all data with `textContent`; no `innerHTML` with data.
- **Injection**: parameterized SQL everywhere; FTS terms wrapped in quoted
  phrases (trigram index tolerates them).
- **Secrets**: API never serializes `.env` values, tokens, `origin_json`, or
  `api_content`; a generic exception handler never leaks internals.
- **DoS guards**: message cap per session (5000), search limits, pagination
  caps (≤1000), 4s SSE poll on small local DBs.

## 6. Remote access (private only)

- Default: `127.0.0.1:9118` — nothing leaves the Mini.
- MacBook/iPhone: `tailscale serve --bg 9118` (tailnet HTTPS) or SSH tunnel.
- Never expose publicly; the dashboard at 9119 (Nous OAuth) is the public
  surface already.

## 7. Implementation phases (as executed)

| Phase | Status |
|---|---|
| 1. Discovery (env, state.db, dashboard API, delegation) | ✅ |
| 2. Data access (`db.py`, `models.py`) | ✅ |
| 3. Aggregation + sessions API (`aggregate.py`, `api.py`) | ✅ |
| 4. Dashboard UI (Overview/Sessions/Detail/Agents/Search) | ✅ |
| 5. Live updates (SSE, turn-lease status) | ✅ |
| 6. Agent/subagent tree visualization | ✅ (detail view) |
| 7. Security (auth, read-only, XSS, injection) | ✅ + review |
| 8. Tests (30 passing) | ✅ |
| 9. Deployment (launchd `ai.hermes.mission-control` :9118) | ✅ |
