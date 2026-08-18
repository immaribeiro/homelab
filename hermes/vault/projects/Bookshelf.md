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
- Download endpoint (byte-exact), detail modal, login screen
- **Library organizer**: `POST /api/organize` + auto-organize on scan (`ORGANIZE_ON_SCAN=true`) — moves new downloads into author folders, MD5-dedupes to `_duplicates/` (idempotent, 0 moves on stable library)
- OPDS 1.2 catalog (root / all books / search) — Kobo-ready

## Status (2026-08-18)

- **Planned** — full implementation plan written (18 tasks), repo scaffolded
- **In progress** — backend (Tasks 1–8, organizer port) + frontend (Tasks 9–14) built in parallel by profile agents; then CI image build, k8s deploy, tunnel route, E2E verification
- **Related session** — Telegram library organization pass (author folders, recursive dedupe pipeline) finalized in `telegram-downloader/`

## Related

- [[Telegram E-book Downloader]] — the source of the library
- [[Homelab Infrastructure]] — where this app is deployed
