---
created: 2026-08-16
updated: 2026-08-16
profile: frontend
model: qwen3.5-9b-mlx
provider: lmstudio
status: active
---

# 🎨 Frontend Agent

UI/UX implementation agent — React, CSS, accessibility. Runs primarily on local LMStudio (free).

## Configuration

| Field | Value |
|-------|-------|
| **Profile** | frontend |
| **Model** | `qwen3.5-9b-mlx` (local 9B model) |
| **Provider** | LMStudio (local) |
| **Cost** | FREE |
| **Fallback 0** | `deepseek/deepseek-v4-flash` via Nous ($0.05/$0.10) |
| **Fallback 1** | `z-ai/glm-5.2` via Nous ($0.25/$0.77) |
| **Config file** | `~/GitHub/homelab/hermes/profiles/frontend/config.yaml` |
| **SOUL.md** | `~/GitHub/homelab/hermes/profiles/frontend/SOUL.md` |
| **Telegram** | 🎨 Frontend topic (thread 5) |
| **Reasoning** | low |
| **Max turns** | 150 |

## LMStudio Model-Slot Strategy

Frontend uses `qwen3.5-9b-mlx` locally; backend falls back to `google/gemma-4-e4b` locally. This avoids model-slot conflicts in LMStudio (one model at a time).

## Toolset Restrictions

Disabled: `tts`, `video`, `video_gen`
Keeps `image_gen` for UI mockups and design references.

## Personality

> You are the **Frontend** agent — a UI/UX implementation engineer specializing in React, CSS, accessibility, and user-facing code. You prefer using local models to keep costs at zero.

## Performance Note

Local 9B model is slower than cloud models (~30s per response vs 1-2s for cloud). The fallback chain ensures quality when local model struggles.

## Command Aliases

```bash
frontend chat          # start interactive chat
frontend doctor        # health check
frontend config set …  # change settings
```

## Related

- [[Agent Overview]]
- [[Telegram Routing]]
- [[Architect Agent]]
- [[Backend Agent]]
