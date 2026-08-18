---
created: 2026-08-18
updated: 2026-08-18
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
| **Library** | `~/Downloads/ebook-library/PT` (~358 books, ~272 author folders) — mounted read-write via hostPath (app organizes) |
| **Deploy** | `k8s/manifests/bookshelf.yml` (namespace `books`), image `ghcr.io/immaribeiro/bookshelf:latest` |
| **Auth** | HTTP Basic (secret `bookshelf-auth`, user `imma`) |
| **Kobo** | OPDS 1.2 feed at `/opds` — future "send to Kobo" path |

## Features

- Cover grid (covers extracted from EPUB metadata), live search, author filter, sort
- **Pagination bar** (prev/next + page numbers) with per-page selector (12/24/48/96)
- **Language filter** (normalized 2-letter codes: pt 307 · en 41 · es 2 · unknown 8) + language badges on covers
- Download endpoint (byte-exact), detail modal, login screen
- **Library organizer**: `POST /api/organize` + auto-organize on scan (`ORGANIZE_ON_SCAN`) — moves new downloads into author folders, MD5-dedupes to `_duplicates/` (idempotent, 0 moves on stable library). Runs on the Mac host; in-cluster returns 409 (Lima mounts home read-only)
- OPDS 1.2 catalog (root / all books / search) — Kobo-ready

## Status (2026-08-18)

**🟢 DEPLOYED & LIVE — https://books.immas.org**

- Backend + frontend built in parallel by profile agents, reviewed + integrated (7/7 tests green)
- Multi-arch image built by GitHub Actions CI → `ghcr.io/immaribeiro/bookshelf:latest`
- Deployed in namespace `books` (pod 1/1 Running), tunnel route + DNS live, homepage card added
- **Login:** username `imma` / password in k8s secret `bookshelf-auth` (ns `books`)
- Verified: auth 401/200, covers (JPEG), downloads byte-identical, OPDS valid XML, search
- **Note:** organization runs on the Mac host (`telegram-downloader` cron pipeline) — Lima VMs mount the Mac home read-only, so the in-app Organize button returns a clean 409 in-cluster (works where the FS is writable)
- **Known issue:** Docker Desktop on the Mini can't pull images (VM network) — CI builds used instead; restart Docker Desktop to fix local builds

## Related

- [[Telegram E-book Downloader]] — the source of the library
- [[Homelab Infrastructure]] — where this app is deployed
