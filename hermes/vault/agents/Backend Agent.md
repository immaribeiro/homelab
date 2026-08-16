---
created: 2026-08-16
updated: 2026-08-16
profile: backend
model: deepseek/deepseek-v4-flash
provider: nous
status: active
---

# ⚙️ Backend Agent

Focused implementation agent for server-side code, APIs, databases, and infrastructure.

## Configuration

| Field | Value |
|-------|-------|
| **Profile** | backend |
| **Model** | `deepseek/deepseek-v4-flash` (coding model) |
| **Provider** | Nous Portal (OAuth) |
| **Cost** | $0.05 in / $0.10 out per 1M tokens (ultra-cheap) |
| **Fallback 0** | `lmstudio/google/gemma-4-e4b` (local, free — different model than frontend) |
| **Fallback 1** | `z-ai/glm-5.2` via Nous |
| **Config file** | `~/GitHub/homelab/hermes/profiles/backend/config.yaml` |
| **SOUL.md** | `~/GitHub/homelab/hermes/profiles/backend/SOUL.md` |
| **Telegram** | ⚙️ Backend topic (thread 4) |
| **Reasoning** | low |
| **Max turns** | 150 |

## LMStudio Model-Slot Strategy

Frontend uses `qwen3.5-9b-mlx` locally; backend falls back to `google/gemma-4-e4b` locally. This avoids model-slot conflicts in LMStudio (one model at a time).

## Toolset Restrictions

Disabled: `tts`, `image_gen`, `video`, `video_gen`

## Personality

> You are the **Backend** agent — a focused implementation engineer specializing in server-side code, APIs, databases, and infrastructure. You work fast, iterate in small steps, and write tests as you go.

## Command Aliases

```bash
backend chat          # start interactive chat
backend doctor        # health check
backend config set …  # change settings
```

## Related

- [[Agent Overview]]
- [[Telegram Routing]]
- [[Architect Agent]]
- [[Frontend Agent]]
