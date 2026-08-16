---
created: 2026-08-16
updated: 2026-08-16
---

# ⚙️ Hermes Config

How Hermes configuration files are organized and synced to git.

## Directory Structure

```
~/GitHub/homelab/hermes/           ← git-tracked (repo)
├── config.yaml                    ← main agent config (symlinked from ~/.hermes/)
├── hermes.json                    ← provider/model definitions
├── SOUL.md                        ← main agent personality
├── memories/
│   ├── MEMORY.md                  ← agent persistent memory
│   └── USER.md                    ← user profile
├── cron/
│   └── jobs.json                  ← scheduled jobs
├── profiles/
│   ├── architect/                 ← architect agent configs
│   ├── backend/                   ← backend agent configs
│   ├── frontend/                  ← frontend agent configs
│   └── engineer/                  ← engineer agent configs
├── docs/
│   └── telegram-routing.md        ← Telegram setup guide
└── vault/                         ← this Obsidian vault

~/.hermes/                         ← runtime home (symlinks point to repo)
├── config.yaml → symlink → ~/GitHub/homelab/hermes/config.yaml
├── hermes.json → symlink → …
├── SOUL.md → symlink → …
├── memories/MEMORY.md → symlink → …
├── memories/USER.md → symlink → …
├── cron/jobs.json → symlink → …
├── .env                           ← SECRETS (never synced)
├── auth.json                      ← OAUTH tokens (never synced)
├── state.db                       ← session store (never synced)
├── sessions/                      ← transcripts (never synced)
├── logs/                          ← logs (never synced)
└── profiles/
    ├── architect/
    │   ├── config.yaml → symlink → repo
    │   ├── hermes.json → symlink → repo
    │   ├── SOUL.md → symlink → repo
    │   ├── memories/ → symlink → repo
    │   └── .env                    ← SECRETS (never synced)
    ├── backend/ (same structure)
    ├── frontend/ (same structure)
    └── engineer/ (same structure)
```

## What's Synced vs Not Synced

| Synced to Git | NOT Synced (local only) |
|----------------|--------------------------|
| config.yaml | .env (API keys) |
| hermes.json | auth.json (OAuth tokens) |
| SOUL.md | state.db (session store) |
| memories/MEMORY.md | sessions/ (transcripts) |
| memories/USER.md | logs/ |
| cron/jobs.json | cron/executions.db |
| profile configs | profile .env files |

## On a New Machine

```bash
# Clone the repo
git clone https://github.com/immaribeiro/homelab.git ~/GitHub/homelab

# Create symlinks
cd ~/.hermes
ln -s ~/GitHub/homelab/hermes/config.yaml config.yaml
ln -s ~/GitHub/homelab/hermes/hermes.json hermes.json
ln -s ~/GitHub/homelab/hermes/SOUL.md SOUL.md
ln -s ~/GitHub/homelab/hermes/memories/MEMORY.md memories/MEMORY.md
ln -s ~/GitHub/homelab/hermes/memories/USER.md memories/USER.md
ln -s ~/GitHub/homelab/hermes/cron/jobs.json cron/jobs.json

# Create profiles with symlinks
for profile in architect backend frontend engineer; do
  hermes profile create $profile
  cd ~/.hermes/profiles/$profile
  ln -sf ~/GitHub/homelab/hermes/profiles/$profile/config.yaml config.yaml
  ln -sf ~/GitHub/homelab/hermes/profiles/$profile/hermes.json hermes.json
  ln -sf ~/GitHub/homelab/hermes/profiles/$profile/SOUL.md SOUL.md
done

# Copy .env (manually — contains secrets)
cp ~/.hermes/.env ~/.hermes/profiles/architect/.env
# Remove Telegram tokens from secondary profiles
```

## Related

- [[Agent Overview]]
- [[Telegram Routing]]
