---
created: 2026-08-16
updated: 2026-08-16
status: active
schedule: "0 7 * * 0"
---

# 📚 Telegram E-book Downloader

Automated weekly download of e-books from a Telegram channel, running as a Hermes cron job.

## Details

| Field | Value |
|-------|-------|
| **Script** | `~/GitHub/homelab/telegram-downloader/run_downloader.sh` |
| **Source channel** | Telegram chat ID `2152949316` |
| **Download dir** | `~/Downloads/ebook-library/PT` |
| **Schedule** | Every Sunday at 07:00 (`0 7 * * 0`) |
| **Cron job ID** | `17ed147e373f` |
| **Last status** | `ok` (was previously erroring with HTTP 429 — usage limit) |
| **Workdir** | `~/GitHub/homelab/telegram-downloader` |

## Implementation

Multiple downloaders available:
- `downloader.py` — main implementation
- `downloader_botapi.py` — Bot API version
- `downloader_pyrogram.py` — Pyrogram version (used by the cron job)

## Related

- [[Homelab Infrastructure]] — lives in the homelab repo
- [[Hermes Config]] — cron job is defined in `cron/jobs.json` (symlinked to repo)
