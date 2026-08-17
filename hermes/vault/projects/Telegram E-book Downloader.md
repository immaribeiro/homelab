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

## Remaining

- **One-time interactive login**: run `./run_downloader.sh --login` from the
  repo dir with the user present (phone code, or scan QR via
  `/tmp/tg_qr_login.py`). Session file `*.session` is git-ignored.
- **Cron rewire**: point cron job `17ed147e373f` at the wrapper (it already
  uses the repo as workdir). Cron prompt should report script stdout and
  treat exit 2 as "login pending", exit 1 as an alert.
- **First real download test** after login.

## Related

- [[Homelab Infrastructure]] — lives in the homelab repo
- [[Hermes Config]] — cron job is defined in `cron/jobs.json` (symlinked to repo)
