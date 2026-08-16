---
created: 2026-08-16
updated: 2026-08-16
---

# 🤖 Agent Overview

## Summary

Four Hermes agent profiles running on a Mac Mini M4 (24GB), managed through a single gateway with Telegram multiplexing.

## Agent Details

### Main (default)

| Field | Value |
|-------|-------|
| **Profile** | default |
| **Config** | `~/.hermes/config.yaml` |
| **Model** | `z-ai/glm-5.2` via Nous |
| **Cost** | $0.25 in / $0.77 out per 1M |
| **Fallback** | OpenAI gpt-5.6-luna → LMStudio qwen3.5 |
| **Telegram** | General topic (thread 1) + personal DM |
| **Role** | General-purpose assistant, daily tasks, conversation |
| **Tools** | Full toolset (web, terminal, file, image_gen, etc.) |

→ [[Main Agent]]

### Architect

| Field | Value |
|-------|-------|
| **Profile** | architect |
| **Config** | `~/GitHub/homelab/hermes/profiles/architect/config.yaml` |
| **Model** | `deepseek/r1-0528` via Nous |
| **Cost** | $0.40 in / $1.72 out per 1M |
| **Fallback** | GLM 5.2 via Nous → LMStudio qwen3.5 |
| **Telegram** | 🏛 Architecture (thread 3) |
| **Role** | System design, reasoning, code review |
| **Tools** | No tts, image_gen, video, video_gen |
| **Reasoning** | high |
| **Max turns** | 120 |

→ [[Architect Agent]]

### Backend

| Field | Value |
|-------|-------|
| **Profile** | backend |
| **Config** | `~/GitHub/homelab/hermes/profiles/backend/config.yaml` |
| **Model** | `qwen/qwen3-coder-30b-a3b` via Nous |
| **Cost** | $0.06 in / $0.22 out per 1M (ultra-cheap) |
| **Fallback** | LMStudio google/gemma-4-e4b → GLM 5.2 |
| **Telegram** | ⚙️ Backend (thread 4) |
| **Role** | Server-side coding, APIs, databases |
| **Tools** | No tts, image_gen, video, video_gen |
| **Reasoning** | low |
| **Max turns** | 150 |

→ [[Backend Agent]]

### Frontend

| Field | Value |
|-------|-------|
| **Profile** | frontend |
| **Config** | `~/GitHub/homelab/hermes/profiles/frontend/config.yaml` |
| **Model** | `qwen3.5-9b-mlx` via LMStudio (local) |
| **Cost** | FREE |
| **Fallback** | Qwen3 Coder 30B via Nous → GLM 5.2 |
| **Telegram** | 🎨 Frontend (thread 5) |
| **Role** | UI/UX, React, CSS, accessibility |
| **Tools** | No tts, video, video_gen |
| **Reasoning** | low |
| **Max turns** | 150 |

→ [[Frontend Agent]]

## Related Projects

Agents work on these projects:
- [[Homelab Infrastructure]] — K3s cluster, networking, deployments
- [[Reconstruction App]] — house reconstruction tracker
- [[Life Dashboard]] — personal dashboard
- [[Telegram E-book Downloader]] — weekly cron job
- [[FlightScanner]] — multi-agent flight price comparison (dev)

## Estimated Daily Cost

| Agent | Est. tokens/day | Cost/day |
|-------|-----------------|----------|
| main | ~50K | ~$0.05 |
| architect | ~30K | ~$0.06 |
| backend | ~100K | ~$0.03 |
| frontend | ~100K (local) | $0.00 |
| **Total** | ~280K | **~$0.14/day** |
