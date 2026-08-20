---
created: 2026-08-16
updated: 2026-08-20
---

# 🤖 Agent Overview

> 🔄 **Last synced:** 2026-08-20 11:56 (auto-sync watchdog, cron `eb7ea48fe83c`)

## Summary

Seven Hermes agent profiles running on a Mac Mini M4 (24GB), managed through a single gateway with Telegram multiplexing.

> **Updated 2026-08-16:** main agent primary switched to `openai-codex` (ChatGPT Go).

## Agent Details

### Main (default)

| Field | Value |
|-------|-------|
| **Profile** | default |
| **Config** | `~/.hermes/config.yaml` |
| **Model** | `gpt-5.6-luna` via openai-codex (ChatGPT Go) |
| **Cost** | ChatGPT subscription (no per-token); fallback $0.05/$0.10 |
| **Fallback** | deepseek-v4-flash via Nous → LMStudio qwen3.5 |
| **Telegram** | General topic (thread 1) + personal DM |
| **Role** | General-purpose assistant, daily tasks, conversation |
| **Tools** | Full toolset (web, terminal, file, image_gen, etc.) |

→ [[Main Agent]]

### Architect

| Field | Value |
|-------|-------|
| **Profile** | architect |
| **Config** | `~/GitHub/homelab/hermes/profiles/architect/config.yaml` |
| **Model** | `deepseek/deepseek-v4-pro-0813` via Nous |
| **Cost** | $0.35 in / $0.70 out per 1M |
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
| **Model** | `deepseek/deepseek-v4-flash` via Nous |
| **Cost** | $0.05 in / $0.10 out per 1M (ultra-cheap) |
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
| **Model** | `deepseek/deepseek-v4-flash` via Nous ($0.05/$0.10) |
| **Cost** | Ultra-cheap (~$0.01/day) |
| **Fallback** | LMStudio qwen3.5-9b-mlx (local, offline) → GLM 5.2 |
| **Telegram** | 🎨 Frontend (thread 5) |
| **Role** | UI/UX, React, CSS, accessibility |
| **Tools** | No tts, video, video_gen |
| **Reasoning** | low |
| **Max turns** | 150 |

→ [[Frontend Agent]]

### Engineer

| Field | Value |
|-------|-------|
| **Profile** | engineer |
| **Config** | `~/GitHub/homelab/hermes/profiles/engineer/config.yaml` |
| **Model** | `deepseek/deepseek-v4-flash` via Nous |
| **Cost** | $0.05 in / $0.10 out per 1M (ultra-cheap) |
| **Fallback** | GLM 5.2 via Nous → LMStudio google/gemma-4-e4b |
| **Telegram** | 🔧 Engineer topic (thread 14) |
| **Role** | IT infra: K3s, Lima VMs, Cloudflare, ArgoCD, troubleshooting |
| **Tools** | No tts, image_gen, video, video_gen |
| **Reasoning** | medium |
| **Max turns** | 200 |
| **Terminal cwd** | `/Users/imma/GitHub/homelab` |

→ [[Engineer Agent]]

### Researcher

| Field | Value |
|-------|-------|
| **Profile** | researcher |
| **Config** | `~/GitHub/homelab/hermes/profiles/researcher/config.yaml` |
| **Model** | `deepseek/deepseek-v4-flash` via Nous |
| **Cost** | $0.05 in / $0.10 out per 1M (ultra-cheap) |
| **Fallback** | GLM 5.2 via Nous → LMStudio qwen3.5-9b-mlx |
| **Telegram** | 🔬 Research topic (thread 431) |
| **Role** | Deep research: web research, market/competitor intel, papers, cited reports |
| **Tools** | No tts, image_gen, video, video_gen |
| **Reasoning** | medium |
| **Max turns** | 120 |
| **Terminal cwd** | `/Users/imma/GitHub` |

→ [[Researcher Agent]]

### Investor

| Field | Value |
|-------|-------|
| **Profile** | investor |
| **Config** | `~/GitHub/homelab/hermes/profiles/investor/config.yaml` |
| **Model** | `deepseek/deepseek-v4-flash` via Nous |
| **Cost** | $0.05 in / $0.10 out per 1M (ultra-cheap) |
| **Fallback** | GLM 5.2 via Nous → LMStudio qwen3.5-9b-mlx |
| **Telegram** | 📈 Investor topic (thread 1016, wired 2026-08-19) |
| **Role** | Markets & portfolio specialist: market/crypto monitoring, news-driven signals, portfolio ops (Revolut X MCP live; Trading 212 API pending) |
| **Tools** | No tts, image_gen, video, video_gen; MCP `revolutx` |
| **Reasoning** | medium |
| **Max turns** | 120 |
| **Terminal cwd** | `/Users/imma/GitHub` |

→ [[Investor Agent]]

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
| main | ~50K | ~$0.00 (subscription; fallback only) |
| architect | ~30K | ~$0.03 |
| backend | ~100K | ~$0.02 |
| frontend | ~100K | ~$0.01 |
| engineer | ~50K | ~$0.01 |
| researcher | ~30K | ~$0.01 |
| investor | ~30K | ~$0.01 |
| **Total** | ~390K | **~$0.09/day** |
