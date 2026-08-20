---
created: 2026-08-18
updated: 2026-08-20
status: active
repo: github.com/immaribeiro/bookshelf
---

# 📚 Bookshelf — E-book Library Web UI

Personal e-book library web app — browse covers, search, and download books from the Telegram library, published at **https://books.immas.org**.

## Details

| Field | Value |
|-------|-------|
| **URL** | `https://books.immas.org` (via Cloudflare tunnel) |
| **Repo** | `~/GitHub/bookshelf` → `github.com/immaribeiro/bookshelf` (private) |
| **Plan** | `.hermes/plans/2026-08-18_075836-bookshelf-library.md` (homelab repo) |
| **Stack** | FastAPI (Python 3.12) + React/Vite/Tailwind, single multi-arch Docker image |
| **Library** | `~/Downloads/ebook-library/` — `PT/` (topic 3, ~358 books) + `ENG/` (topic 5, backfilling 1 GiB/week since 2026-08-20) — mounted read-only via hostPath (writes happen via host sync / Mac cron; Lima mounts home RO) |
| **Deploy** | `k8s/manifests/bookshelf.yml` (namespace `books`, pod pinned to `k3s-worker-1`), image `ghcr.io/immaribeiro/bookshelf:latest` |
| **Auth** | Multi-user HTTP Basic from `BOOKSHELF_USERS` JSON secret — `imma`, `joaoreis` |
| **Kobo** | OPDS 1.2 feed at `/opds` — future "send to Kobo" path |

## Features

- Cover grid (covers extracted from EPUB metadata), live search, author filter, sort
- **Pagination bar** (prev/next + page numbers) with per-page selector (12/24/48/96)
- **Language filter** (normalized 2-letter codes: pt 307 · en 41 · es 2 · unknown 8) + language badges on covers
- **Upload books** (⬆ Upload button): staged on k3s-worker-1 (`/home/imma.linux/bookshelf-uploads`) → host sync (`scripts/bookshelf-upload-sync.sh`, launchd `ai.hermes.bookshelf-upload-sync`, every 3 min) → moved into `PT/` + auto-organized + **rescan triggered** (book visible in ~3 min)
- **Multi-user auth** (HTTP Basic): users from `BOOKSHELF_USERS` JSON secret — `imma`, `joaoreis`
- **📖 Read online**: full-screen reader — epub.js (paginated prev/next + arrow keys, TOC sidebar, A−/A+ font size, **Serif/Sans/Mono** family, **☀️/🌙 light-dark page themes**, progress bar + resume per book, Esc close); PDFs via native viewer (blob URL)
- Download endpoint (byte-exact), detail modal, login screen
- **Library organizer**: `POST /api/organize` + auto-organize on scan (`ORGANIZE_ON_SCAN`) — moves new downloads into author folders, MD5-dedupes to `_duplicates/` (idempotent, 0 moves on stable library). Runs on the Mac host; in-cluster returns 409 (Lima mounts home read-only)
- OPDS 1.2 catalog (root / all books / search) — Kobo-ready

## Status (2026-08-18)

**🟢 DEPLOYED & LIVE — https://books.immas.org**

- Backend + frontend built in parallel by profile agents, reviewed + integrated (9/9 tests green)
- Multi-arch image built by GitHub Actions CI → `ghcr.io/immaribeiro/bookshelf:latest`
- Deployed in namespace `books` (pod 1/1 Running on k3s-worker-1), tunnel route + DNS live, homepage card added
- **Login:** `imma` (original password) · `joaoreis` — passwords in k8s secret `bookshelf-auth` (ns `books`)
- Verified: auth (multi-user 200/401), covers (JPEG), downloads byte-identical, OPDS valid XML, search, **upload round-trip** (UI → staging → sync → organized → grid), **reader** (epub.js renders, pages turn, themes + fonts)
- **Language analysis:** 86% PT (307) · 11.5% EN (41) · 2 ES · 8 unknown — `pt-TT` metadata typo normalized
- **Note:** organization runs on the Mac host (`telegram-downloader` cron pipeline) — Lima VMs mount the Mac home read-only, so in-app Organize/upload-write return 409 in-cluster (uploads stage on the VM disk + host sync instead)
- **Known issue:** Docker Desktop on the Mini can't pull images (VM network) — CI builds used instead; restart Docker Desktop to fix local builds

## Related

- [[Telegram E-book Downloader]] — the source of the library
- [[Homelab Infrastructure]] — where this app is deployed
