---
created: 2026-08-16
updated: 2026-08-16
profile: default
model: deepseek/deepseek-v4-flash
provider: nous
status: active
---

# Main Agent

The default Hermes agent for general-purpose tasks and daily conversation.

## Configuration

| Field | Value |
|-------|-------|
| **Profile** | default (no profile needed — uses `~/.hermes/`) |
| **Model** | `deepseek/deepseek-v4-flash` |
| **Provider** | Nous Portal (OAuth) |
| **Cost** | $0.05 in / $0.10 out per 1M tokens |
| **Fallback 0** | `openai/gpt-5.6-luna` ($0.10/$0.60) |
| **Fallback 1** | `lmstudio/qwen3.5-9b-mlx` (local, free) |
| **Config file** | `~/.hermes/config.yaml` → symlink to `~/GitHub/homelab/hermes/config.yaml` |
| **SOUL.md** | `~/.hermes/SOUL.md` → symlink to repo |
| **Telegram** | Personal DM (chat_id 1022966386) + General topic (thread 1) |

## Delegation

| Field | Value |
|-------|-------|
| **Delegation model** | `gpt-5.6-luna` via Nous |
| **Max children** | 10 |
| **Max spawn depth** | 1 |

## Memory

- `~/.hermes/memories/MEMORY.md` → symlink to repo
- `~/.hermes/memories/USER.md` → symlink to repo
- Memory char limit: 2200
- User profile char limit: 1375

## Related

- [[Agent Overview]]
- [[Telegram Routing]]
- [[Hermes Config]]
