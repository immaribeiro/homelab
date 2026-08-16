---
created: 2026-08-16
updated: 2026-08-16
---

# 🏠 Hermes Agent Hub

Welcome to your Hermes agent management vault. This vault is synced to the homelab git repo and linked to Hermes via `OBSIDIAN_VAULT_PATH`.

## 🤖 Agents

| Agent | Profile | Model | Cost (in/out per 1M) | Telegram Topic |
|-------|---------|-------|----------------------|----------------|
| Main | default | GLM 5.2 via Nous | $0.25 / $0.77 | General |
| Architect | architect | DeepSeek R1 via Nous | $0.40 / $1.72 | 🏛 Architecture |
| Backend | backend | Qwen3 Coder 30B via Nous | $0.06 / $0.22 | ⚙️ Backend |
| Frontend | frontend | Qwen 3.5 9B via LMStudio | FREE | 🎨 Frontend |

→ [[Main Agent]] · [[Architect Agent]] · [[Backend Agent]] · [[Frontend Agent]]

## 📂 Vault Structure

| Folder | Purpose |
|--------|---------|
| `agents/` | One note per agent — config, model, personality, status |
| `projects/` | Project notes — one per active project |
| `decisions/` | Architecture Decision Records (ADRs) |
| `daily/` | Daily logs and journals |
| `notes/` | General-purpose notes |
| `assets/` | Images, attachments |

## 📋 Quick Links

- [[Agent Overview]] — summary table of all agents
- [[Telegram Routing]] — how Telegram topics route to agents
- [[Hermes Config]] — where configs live and how they're synced
- [[Cost Tracking]] — model costs and daily estimates
- [[LMStudio Models]] — local models available

## 🔧 Admin Commands

```bash
# Gateway
hermes gateway restart

# Profile health
hermes -p architect doctor
hermes -p backend doctor
hermes -p frontend doctor

# Profile chat
hermes -p architect chat
hermes -p backend chat
hermes -p frontend chat

# Open vault in Obsidian
open ~/GitHub/homelab/hermes/vault
```
