---
created: 2026-08-16
updated: 2026-08-18
---

# 📱 Telegram Routing

How Telegram messages route to different Hermes agent profiles.

## Architecture

Single Telegram bot (`@ImmaHermesBot`) → single gateway → `profile_routes` directs each topic to its agent.

```
@ImmaHermesBot (1 bot)
       │
  Hermes Gateway (multiplex_profiles: true)
       │
  ┌────┼────┬────┬────┬────┬────┐
  │    │    │    │    │    │    │
 main arch back front eng  research
```

## Live Configuration

**Group:** "Hermes" (supergroup with forum topics)
**Chat ID:** `-1004449482428`

| Topic | Thread ID | Profile | Agent |
|-------|-----------|---------|-------|
| General | 1 | default | [[Main Agent]] |
| 🏛 Architecture | 3 | architect | [[Architect Agent]] |
| ⚙️ Backend | 4 | backend | [[Backend Agent]] |
| 🎨 Frontend | 5 | frontend | [[Frontend Agent]] |
| 🔧 Engineer | 14 | engineer | [[Engineer Agent]] |
| 🔬 Research | 431 | researcher | [[Researcher Agent]] |

**Personal DM** (chat_id `1022966386`) → always goes to default (main) — no route needed.

## How Routes Work

- Routes match **most-specific-first**: `thread_id` > `chat_id` > `guild_id`
- All declared fields must hold (AND logic)
- Messages matching **no route** stay on the default profile
- `profile_routes` requires `gateway.multiplex_profiles: true`

## Credential Rule

Only the **default profile** (`~/.hermes/.env`) has `TELEGRAM_BOT_TOKEN`. Secondary profiles must NOT have Telegram credentials — the multiplexer uses the single connection.

## config.yaml

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
    - name: tg-engineer
      platform: telegram
      chat_id: "-1004449482428"
      thread_id: "14"
      profile: engineer
    - name: tg-researcher
      platform: telegram
      chat_id: "-1004449482428"
      thread_id: "431"
      profile: researcher
```

## Full Documentation

→ [hermes/docs/telegram-routing.md](../../docs/telegram-routing.md) in the homelab repo

## Related

- [[Agent Overview]]
- [[Hermes Config]]
