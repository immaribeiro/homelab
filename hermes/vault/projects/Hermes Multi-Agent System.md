---
created: 2026-08-16
updated: 2026-08-21
status: active
---

# 🧠 Hermes Multi-Agent System

Hermes Agent framework configured on the Mac Mini with 7 agent profiles (main + 6), Telegram routing, and Obsidian vault integration.

## Details

| Field | Value |
|-------|-------|
| **Version** | Hermes Agent 0.20.1 |
| **Hub machine** | Mac Mini M4 (imma-mini, 100.101.63.91) |
| **Config location** | `~/GitHub/homelab/hermes/` (git-synced via symlinks) |
| **Vault location** | `~/GitHub/homelab/hermes/vault/` (this Obsidian vault) |
| **Telegram bot** | @ImmaHermesBot |
| **Telegram group** | "Hermes" (forum, chat_id -1004449482428) |
| **Gateway** | launchd: `ai.hermes.gateway` (multiplex_profiles: true) |
| **Dashboard** | launchd: `ai.hermes.dashboard` on :9119 |
| **Cost** | ~$0.09/day (~$2.70/month) |

## Agents

→ [[Main Agent]] · [[Architect Agent]] · [[Backend Agent]] · [[Frontend Agent]] · [[Engineer Agent]] · [[Researcher Agent]] · [[Investor Agent]]

## Key Features

- **Profile multiplexing** — single gateway, single bot, 7 isolated agent profiles (main, architect, backend, frontend, engineer, researcher, investor)
- **Telegram topic routing** — each topic maps to a different agent (see [[Telegram Routing]])
- **Cost-optimized models** — all worker profiles run DeepSeek V4 Flash via Nous (ultra-cheap) with local LMStudio as offline fallback; architect uses V4 Pro 0813 for deep reasoning; main runs on the ChatGPT subscription (GPT-5.6 Luna)
- **Git-synced configs** — all configs version-controlled in the homelab repo
- **Obsidian vault** — agent management UI, project notes, ADRs, accessible from any machine via SMB/Tailscale

## Related

- [[Agent Overview]] — full agent comparison table
- [[Telegram Routing]] — how topics route to agents
- [[Hermes Config]] — config sync structure
- [[Cost Tracking]] — model costs and daily estimates
- [[Remote Vault Access]] — connecting from other machines
