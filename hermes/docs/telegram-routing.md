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

## Topic → Agent Mapping

| Telegram Topic | Thread ID | Profile | Model | Cost |
|----------------|-----------|---------|-------|------|
| General | (default/topic 1) | main (default) | GLM 5.2 | $0.25/$0.77 |
| 🏛 Architecture | (topic 2) | architect | DeepSeek R1 | $0.40/$1.72 |
| ⚙️ Backend | (topic 3) | backend | Qwen3 Coder 30B | $0.06/$0.22 |
| 🎨 Frontend | (topic 4) | frontend | LMStudio (local) | FREE |

## Setup Steps (One-Time)

### Step 1: Create a Telegram Group with Topics

1. Open Telegram → New Group → Add `@ImmaHermesBot` → Name it "Hermes Agents" (or whatever you like)
2. Go to Group Settings → Edit → **Turn on Topics** (this converts it to a forum group)
3. Make `@ImmaHermesBot` an **admin** with "Read all messages" permission (required for bots in groups)
4. Create topics:
   - **General** (already exists as the "General" topic)
   - **🏛 Architecture**
   - **⚙️ Backend**
   - **🎨 Frontend**

### Step 2: Get the Chat ID and Thread IDs

Send any message in each topic, then check the gateway logs or use the Telegram API:

```bash
# The group chat ID (negative number, e.g. -1001234567890)
# Each topic has a message_thread_id (a positive number)
# You can find these by sending a message in each topic and checking:
tail -f ~/.hermes/logs/gateway.log | grep "chat_id\|thread"
```

Or ask the main agent (me) to look it up:
```bash
hermes chat -q "What was the last Telegram chat_id and thread_id you received?"
```

### Step 3: Configure profile_routes in config.yaml

Once you have the group chat_id and thread_ids, update `~/.hermes/config.yaml` (which is symlinked to the repo):

```yaml
gateway:
  multiplex_profiles: true
  profile_routes:
    # General topic → main (default — no route needed, unmatched goes to default)
    # But if you want explicit routing:
    - name: tg-general
      platform: telegram
      chat_id: "-100XXXXXXXXXX"       # your group chat ID
      thread_id: "1"                  # General topic is always thread_id 1
      profile: default

    # Architecture topic → architect
    - name: tg-architect
      platform: telegram
      chat_id: "-100XXXXXXXXXX"       # same group chat ID
      thread_id: "XXXXX"              # Architecture topic's thread_id
      profile: architect

    # Backend topic → backend
    - name: tg-backend
      platform: telegram
      chat_id: "-100XXXXXXXXXX"
      thread_id: "XXXXX"              # Backend topic's thread_id
      profile: backend

    # Frontend topic → frontend
    - name: tg-frontend
      platform: telegram
      chat_id: "-100XXXXXXXXXX"
      thread_id: "XXXXX"              # Frontend topic's thread_id
      profile: frontend
```

**Important:** Replace `-100XXXXXXXXXX` with your actual group chat ID and `XXXXX` with the actual thread IDs.

### Step 4: Restart the Gateway

```bash
hermes gateway restart
```

### Step 5: Test

Send a message in each topic:
- "General" topic → should get a response from the main agent (GLM 5.2)
- "🏛 Architecture" topic → should get a response from the architect (DeepSeek R1, slower but deeper)
- "⚙️ Backend" topic → should get a response from the backend agent (Qwen3 Coder)
- "🎨 Frontend" topic → should get a response from the frontend agent (local LMStudio)

## How to Identify Which Agent Responded

Each profile has a different SOUL.md personality, so:
- **main** — general, helpful assistant
- **architect** — refers to tradeoffs, ADRs, system boundaries
- **backend** — talks about APIs, tests, server-side code
- **frontend** — talks about UI, CSS, accessibility, components

You can also ask any agent: "What model are you running?" and it will tell you.

## Maintenance

### Adding a New Agent Profile

1. Create the profile: `hermes profile create <name> --description "role"`
2. Write config.yaml, hermes.json, SOUL.md in `~/GitHub/homelab/hermes/profiles/<name>/`
3. Symlink: `ln -s ~/GitHub/homelab/hermes/profiles/<name>/config.yaml ~/.hermes/profiles/<name>/config.yaml` (etc.)
4. Copy .env: `cp ~/.hermes/.env ~/.hermes/profiles/<name>/.env`
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
- **Gateway doesn't start** → Run `hermes doctor` and check `~/.hermes/logs/gateway.log`
- **Profile not found** → Run `hermes profile list` to verify profiles exist
- **Same token conflict** → All profiles share the same bot token — this is fine with multiplexing. Don't start separate gateways per profile.

## Reference

- [Hermes Profiles Documentation](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [Multi-Profile Gateways](https://hermes-agent.nousresearch.com/docs/user-guide/multi-profile-gateways)
- [Telegram Setup](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)
