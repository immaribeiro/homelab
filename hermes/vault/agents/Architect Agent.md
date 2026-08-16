---
created: 2026-08-16
updated: 2026-08-16
profile: architect
model: deepseek/r1-0528
provider: nous
status: active
---

# 🏛 Architect Agent

Deep reasoning agent for system design, architecture decisions, and code review.

## Configuration

| Field | Value |
|-------|-------|
| **Profile** | architect |
| **Model** | `deepseek/r1-0528` (reasoning model) |
| **Provider** | Nous Portal (OAuth) |
| **Cost** | $0.40 in / $1.72 out per 1M tokens |
| **Fallback 0** | `z-ai/glm-5.2` via Nous |
| **Fallback 1** | `lmstudio/qwen3.5-9b-mlx` (local, free) |
| **Config file** | `~/GitHub/homelab/hermes/profiles/architect/config.yaml` |
| **SOUL.md** | `~/GitHub/homelab/hermes/profiles/architect/SOUL.md` |
| **Telegram** | 🏛 Architecture topic (thread 3) |
| **Reasoning** | high |
| **Max turns** | 120 |

## Toolset Restrictions

Disabled: `tts`, `image_gen`, `video`, `video_gen`

## Personality

> You are the **Architect** agent — a senior systems architect focused on design, planning, and code review. You think deeply about tradeoffs, system boundaries, and long-term maintainability.

## Command Aliases

```bash
architect chat          # start interactive chat
architect doctor        # health check
architect config set …  # change settings
```

## Related

- [[Agent Overview]]
- [[Telegram Routing]]
- [[Backend Agent]]
- [[Frontend Agent]]
