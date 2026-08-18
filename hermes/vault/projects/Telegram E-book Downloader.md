---
created: 2026-08-16
updated: 2026-08-17
status: active
schedule: "0 7 * * 0"
---

# 📚 Telegram E-book Downloader

Automated weekly download of e-books from a private Telegram channel, running as a Hermes cron job.

## Details

| Field | Value |
|-------|-------|
| **Script** | `~/GitHub/homelab/telegram-downloader/run_downloader.sh` |
| **Source channel** | Private channel, chat ID `-1002152949316` (`https://t.me/c/2152949316/3`) |
| **Download dir** | `~/Downloads/ebook-library/PT` |
| **Schedule** | Every Sunday at 07:00 (`0 7 * * 0`) |
| **Cron job ID** | `17ed147e373f` |
| **Workdir** | `~/GitHub/homelab/telegram-downloader` |
| **Env file** | `~/.hermes/env/telegram-downloader.env` (credentials, outside repo) |

## Status (2026-08-17)

**WORKING — first full sync succeeded.**

Rewritten by architect + backend profile agents (commit `10f3d6e`):

- **`downloader.py`** — canonical Telethon implementation. Env-file config
  (CLI > env var > env-file > default), `--login` interactive auth,
  headless cron-safe mode, chat resolver (`-100` prefix / t.me links /
  legacy strings), FloodWait 429 retry, filename dedupe, sanitized
  filenames, honest exit codes: 0 success, 1 config/run error, 2 session
  missing.
- **`run_downloader.sh`** — headless cron wrapper: sources env file, uses
  `.venv/bin/python`, execs downloader.py so exit codes propagate.
- **Deleted** `downloader_botapi.py` (Bot API can't read private channel
  history) and `downloader_pyrogram.py` (pyrogram never installed).
- Added `.gitignore` (`.session`, `.venv`); hardcoded API secret removed
  from tracked code; pyproject now declares telethon.
- Env `TELEGRAM_TARGET_CHAT` fixed to `-1002152949316` (was bogus
  `39155241:c/2152949316`).

### Login (done 2026-08-17)

Session created via QR login (scanned from phone). Session file
`testbot.session` in the repo dir, git-ignored. To re-login later:
`./run_downloader.sh --login` (phone code) or QR flow.

### First sync result (2026-08-17)

- **370 books / 1.4 GB** downloaded into `~/Downloads/ebook-library/PT`
- First run: 272 downloaded, 124 skipped (dup), 0 failed, exit 0
- Re-run (dedupe check): 0 downloaded, 396 skipped, 0 failed, exit 0 in 2.4s
- Cron rewired to the working wrapper; weekly Sunday 07:00

## Related

- [[Bookshelf]] — web UI for this library (**live at https://books.immas.org**, built 2026-08-18)
- [[Homelab Infrastructure]] — lives in the homelab repo
- [[Hermes Config]] — cron job is defined in `cron/jobs.json` (symlinked to repo)
