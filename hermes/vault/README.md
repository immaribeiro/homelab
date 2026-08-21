---
created: 2026-08-16
updated: 2026-08-21
---

# 🏠 Hermes Agent Hub

Welcome to your Hermes agent management vault. This vault is synced to the homelab git repo and linked to Hermes via `OBSIDIAN_VAULT_PATH`. Accessible from any machine via SMB over Tailscale.

## 🤖 Agents

| Agent | Profile | Model | Cost (in/out per 1M) | Telegram Topic |
|-------|---------|-------|----------------------|----------------|
| Main | default | GPT-5.6 Luna (ChatGPT Go) | subscription | General |
| Architect | architect | DeepSeek V4 Pro 0813 via Nous | $0.35 / $0.70 | 🏛 Architecture |
| Backend | backend | DeepSeek V4 Flash via Nous | $0.05 / $0.10 | ⚙️ Backend |
| Frontend | frontend | DeepSeek V4 Flash via Nous | $0.05 / $0.10 | 🎨 Frontend |
| Engineer | engineer | DeepSeek V4 Flash via Nous | $0.05 / $0.10 | 🔧 Engineer |
| Researcher | researcher | DeepSeek V4 Flash via Nous | $0.05 / $0.10 | 🔬 Research |
| Investor | investor | DeepSeek V4 Flash via Nous | $0.05 / $0.10 | 📈 Investor |

→ [[Agent Overview]] · [[Main Agent]] · [[Architect Agent]] · [[Backend Agent]] · [[Frontend Agent]] · [[Engineer Agent]] · [[Researcher Agent]] · [[Investor Agent]]

## 📂 Projects

| Project | Status | Description |
|---------|--------|-------------|
| [[Homelab Infrastructure]] | Active | K3s cluster on Mac Mini M4 via Lima VMs |
| [[Hermes Multi-Agent System]] | Active | 7-agent setup with Telegram routing + Obsidian vault |
| [[Reconstruction App]] | Active | House reconstruction tracker (FastAPI + PostgreSQL) |
| [[Life Dashboard]] | Active | Personal dashboard backend (FastAPI + SQLModel) |
| [[Japan Planner]] | Active | Japan trip planning app |
| [[FlightScanner]] | Dev | Multi-agent flight price comparison (not deployed) |
| [[Telegram E-book Downloader]] | Active | Weekly PT+ENG e-book sync from Floresta Encantada topics (cron Sun 07:00) |
| [[Bookshelf]] | Active | E-book library web UI — live at https://books.immas.org |

## 📋 Reference Notes

- [[Telegram Routing]] — how Telegram topics route to agents
- [[Hermes Config]] — where configs live and how they're synced
- [[Cost Tracking]] — model costs and daily estimates
- [[LMStudio Models]] — local models available
- [[Remote Vault Access]] — connecting from other machines

## 🏛 Decisions

- [[ADR-001 Architecture Review]] — initial homelab architecture assessment (2025-06-28)

## 📂 Vault Structure

| Folder | Purpose |
|--------|---------|
| `agents/` | One note per agent — config, model, personality, status |
| `projects/` | Project notes — one per active project |
| `decisions/` | Architecture Decision Records (ADRs) |
| `daily/` | Daily logs and journals |
| `notes/` | General-purpose reference notes |
| `assets/` | Images, attachments |

## 🔧 Admin Commands

```bash
# Gateway
hermes gateway restart

# Profile health
hermes -p architect doctor
hermes -p backend doctor
hermes -p frontend doctor
hermes -p engineer doctor
hermes -p researcher doctor
hermes -p investor doctor

# Profile chat
hermes -p architect chat
hermes -p backend chat
hermes -p frontend chat
hermes -p engineer chat
hermes -p researcher chat
hermes -p investor chat

# Open vault in Obsidian
open ~/GitHub/homelab/hermes/vault
```
