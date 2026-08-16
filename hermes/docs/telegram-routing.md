# Telegram Multi-Agent Routing Setup Guide

## Architecture

All four Hermes agents (main, architect, backend, frontend) share a single Telegram bot (`@ImmaHermesBot`) and a single gateway process. The gateway uses **profile multiplexing** to route messages from different Telegram Topics to different agent profiles.

```
                    ┌──────────────────────────┐
                    │   @ImmaHermesBot          │
                    │   (single Telegram bot)    │
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │   Hermes Gateway          │
                    │   (multiplex_profiles)    │
                    │   ai.hermes.gateway       │
                    └──────────┬───────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼───┐  ┌────────▼───┐  ┌────────▼───┐  ┌────────────┐
     │  main      │  │ architect  │  │  backend   │  │  frontend  │
     │  (default) │  │  profile   │  │  profile   │  │  profile   │
     │  GLM 5.2   │  │ DeepSeek R1│  │ Qwen3 Coder│  │ LMStudio   │
     └────────────┘  └────────────┘  └────────────┘  └────────────┘
```

## How It Works

1. **One Telegram group** with **Topics (forum threads)** — each topic maps to one agent
2. The gateway multiplexer routes inbound messages to the right profile based on `thread_id`
3. Each profile has its own model, SOUL, memory, and toolset — completely isolated
4. All profiles share the same bot token (no need for multiple bots)

## Current Configuration (Live)

| Telegram Topic | Thread ID | Profile | Model | Cost (in/out per 1M) |
|----------------|-----------|---------|-------|----------------------|
| General | 1 | default (main) | GLM 5.2 via Nous | $0.25 / $0.77 |
| 🏛 Architecture | 3 | architect | DeepSeek R1 via Nous | $0.40 / $1.72 |
| ⚙️ Backend | 4 | backend | Qwen3 Coder 30B via Nous | $0.06 / $0.22 |
| 🎨 Frontend | 5 | frontend | Qwen 3.5 9B via LMStudio | FREE |

**Group chat ID:** `-1004449482428` (group name: "Hermes")

**Your personal DM** (chat ID `1022966386`) always goes to the default (main) profile — no route needed.

## config.yaml Excerpt (Live)

```yaml
gateway:
  multiplex_profiles: true
  profile_routes:
    - name: tg-general
      platform: telegram
      chat_id: "-1004449482428"
      thread_id: "1"
      profile: default

    - name: tg-architect
      platform: telegram
      chat_id: "-1004449482428"
      thread_id: "3"
      profile: architect

    - name: tg-backend
      platform: telegram
      chat_id: "-1004449482428"
      thread_id: "4"
      profile: backend

    - name: tg-frontend
      platform: telegram
      chat_id: "-1004449482428"
      thread_id: "5"
      profile: frontend
```

## Important: Telegram Credentials

When multiplexing is enabled, **only the default profile** (`~/.hermes/.env`) should have `TELEGRAM_BOT_TOKEN`. The secondary profiles (architect, backend, frontend) must NOT have Telegram credentials — the multiplexer handles the single Telegram connection and routes via `profile_routes`.

If secondary profiles have Telegram tokens, the gateway will refuse to start with:
```
ERROR: Profile 'default' and 'backend' both configure telegram with the same credential
```

Fix: remove `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, and `TELEGRAM_HOME_CHANNEL` from each profile's `.env`.

## How to Identify Which Agent Responded

Each profile has a different SOUL.md personality:
- **main** — general, helpful assistant
- **architect** — refers to tradeoffs, ADRs, system boundaries
- **backend** — talks about APIs, tests, server-side code
- **frontend** — talks about UI, CSS, accessibility, components

Ask any agent: "What model are you?" and it will tell you.

## Maintenance

### Adding a New Agent Profile

1. Create: `hermes profile create <name> --description "role"`
2. Write config.yaml, hermes.json, SOUL.md in `~/GitHub/homelab/hermes/profiles/<name>/`
3. Symlink: `ln -s ~/GitHub/homelab/hermes/profiles/<name>/config.yaml ~/.hermes/profiles/<name>/config.yaml` (etc.)
4. Copy .env: `cp ~/.hermes/.env ~/.hermes/profiles/<name>/.env` (then remove Telegram credentials from it)
5. Create a new Telegram topic in the group
6. Add a `profile_routes` entry with the new thread_id
7. `hermes gateway restart`

### Changing a Profile's Model

Edit `~/GitHub/homelab/hermes/profiles/<name>/config.yaml` → change `model.default` and `model.provider`. Restart gateway.

### Disabling an Agent

Remove the profile route from config.yaml (or set `gateway.multiplex_profile_allowlist` to only the profiles you want active). Restart gateway.

## Troubleshooting

- **Bot doesn't respond in topics** → Ensure bot is admin with "Read all messages" in the group
- **Wrong agent responds** → Check `thread_id` matches the topic. Routes match most-specific-first (thread_id > chat_id > guild_id)
- **"same credential" error** → Remove `TELEGRAM_BOT_TOKEN` from secondary profile `.env` files. Only the default profile needs it.
- **Gateway doesn't start** → Run `hermes doctor` and check `~/.hermes/logs/gateway.log`
- **Profile not found** → Run `hermes profile list` to verify profiles exist

## Reference

- [Hermes Profiles Documentation](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [Multi-Profile Gateways](https://hermes-agent.nousresearch.com/docs/user-guide/multi-profile-gateways)
- [Telegram Setup](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)
