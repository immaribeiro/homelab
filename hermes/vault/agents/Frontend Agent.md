---
created: 2026-08-16
updated: 2026-08-21
profile: frontend
model: deepseek/deepseek-v4-flash
provider: nous
status: active
---

# 🎨 Frontend Agent

UI/UX implementation agent — React, CSS, accessibility. Runs on DeepSeek V4 Flash via Nous (ultra-cheap); local LMStudio as offline fallback.

## Configuration

| Field | Value |
|-------|-------|
| **Profile** | frontend |
| **Model** | `deepseek/deepseek-v4-flash` via Nous ($0.05/$0.10) |
| **Provider** | Nous |
| **Cost** | Ultra-cheap (~$0.01/day) |
| **Fallback 0** | `qwen3.5-9b-mlx` via LMStudio (local, free — offline) |
| **Fallback 1** | `z-ai/glm-5.2` via Nous ($0.25/$0.77) |
| **Config file** | `~/GitHub/homelab/hermes/profiles/frontend/config.yaml` |
| **SOUL.md** | `~/GitHub/homelab/hermes/profiles/frontend/SOUL.md` |
| **Telegram** | 🎨 Frontend topic (thread 5) |
| **Reasoning** | low |
| **Max turns** | 150 |

## LMStudio Model-Slot Strategy

Frontend's primary is now `deepseek/deepseek-v4-flash` via Nous; `qwen3.5-9b-mlx` (LMStudio) is the offline fallback when Nous is unreachable. Backend falls back to `google/gemma-4-e4b` locally — the model-slot strategy still avoids LMStudio conflicts (one model at a time).

## Toolset Restrictions

Disabled: `tts`, `video`, `video_gen`
Keeps `image_gen` for UI mockups and design references.

## MCP Servers (live 2026-08-21)

| Server | Endpoint | Tools | Status |
|--------|----------|-------|--------|
| `figma` | `https://mcp.figma.com/mcp` | 36 (`mcp__figma__*`) | ✅ connected (OAuth) |
| `vercel` | `https://mcp.vercel.com` | 38 (`mcp__vercel__*`) | ✅ connected (OAuth) |

- **Tools:** design context, screenshot, generate Figma design, diagram, shaders; Vercel deploy, projects, domains, runtime logs, docs search.
- **Config:** `mcp_servers` in `~/.hermes/profiles/frontend/config.yaml` (both `auth: oauth`, `enabled: true`).
- **Tokens:** `~/.hermes/profiles/frontend/mcp-tokens/` (`figma.json`, `vercel.json`).
- **Verify:** `HERMES_HOME=~/.hermes/profiles/frontend hermes mcp test figma|vercel`

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
