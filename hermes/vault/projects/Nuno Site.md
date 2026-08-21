# Nuno Site (nuno.immas.org)

Private couple site for Imma + Nuno. Static Vite + React + Tailwind v3, deployed to K3s (namespace `nuno`), CI via GitHub Actions → ghcr → manual rollout.

## Pages

1. **The archive** — photo gallery (manifest.json / photos/).
2. **Events** — Porto/Braga cultural events, prices, topic chips (user-added; `topics.json` `focus` default is empty since 2026-08-21 — jazz/fado no longer pre-selected), star pins (personal + shared `pinned.json`).
3. **News** — 5 categories (Portugal / Porto & Braga / Mundo / Música / IA), addable topics, quotas per category.
4. **Us** — weather (Open-Meteo), days-together counter, date-ideas bucket list (🎲 Surpresa), milestones, songs. Config: `public/couple.json`.
5. **Hermes** — direct chat with the assistant (see below).

## Pipelines (daily 06:00, `~/.hermes/scripts/events-fetch.sh`)

- `fetch_events.py` → `public/events.json` (venues + Eventbrite browse-page scraping, keyless, price enrichment from detail pages).
- **Curated events**: hand-picked calendar entries live in `MANUAL_EVENTS` inside `fetch_events.py` — they survive the daily refresh and bypass the 14-day window (shown as soon as marked). Used e.g. for Verde Cool (Braga, 7 set–4 out).
- `fetch_news.py` → `public/news.json` (stdlib RSS/Atom, quotas, idempotent).
- **Live data (2026-08-21):** events/news/topics/pinned/couple/quotes are served from a read-only hostPath mount of `public/` → `/mnt/site-data` (nginx exact-match aliases, no-cache) — **the same pattern as photos**. The daily fetch commits+pushes as backup only; CI has `paths-ignore` for all data JSONs, so **data refreshes never build an image**. New data goes live the instant the host file changes (~1 s). Code changes still build + the `ghcr-deploy-watch` launchd agent (`~/.hermes/scripts/ghcr-deploy-watch.sh`, every 180 s) auto-rolls the deployment — nuno-site was added to its `APPS` list (2026-08-21).
- **Manual refresh:** Events and News pages have an **"Update now ↻"** button → `POST /api/refresh` on the bridge (same SITE_TOKEN auth) → runs both fetchers on the host → live immediately.

## Chat with Hermes

Browser → Cloudflare → K3s nginx → `/api/` upstream (dual-IP failover) → **nuno-chat-bridge** on the hub (launchd `ai.hermes.nuno-chat-bridge`, :8643) → **Hermes API server** (:8642, inside the gateway, enabled via `gateway.api_server` in `~/.hermes/config.yaml`) → agent session `nuno-site`.

- Secrets: `~/.hermes/env/nuno-chat-bridge.env` (chmod 600) — `HERMES_API_KEY` == `API_SERVER_KEY`, `SITE_TOKEN` == `SITE_TOKEN` in `src/config.js`.
- Code + docs: `~/GitHub/homelab/nuno-chat-bridge/`.
- Bridge reply path verified by `restart-and-verify.sh` (one-shot launchd job, reports to Telegram).
- **Persona (2026-08-19):** system prompt defines Imma as a **man** («ele», «o Imma») and Nuno as his partner — gay couple; agent must never use feminine forms for Imma (fixes misgendering in chat replies).

## Photo upload (2026-08-20 — live, no rebuild)

The archive page has an **"Add a photo +"** button (mobile-friendly file picker) → `POST /api/upload` on the bridge:
1. Saves to `~/GitHub/nuno-site/src_photos/` (gitignored, originals stay local)
2. Runs `pipeline.py` → optimized WebP + atomic manifest (writes both `public/manifest.json` and a live copy `public/photos/manifest.json`)
3. Response returns **instantly (~0.3 s)** — the pod serves the photo live from a read-only hostPath mount of `public/photos` → `/mnt/photos` (nginx aliases `/photos/` immutable + `/manifest.json` no-cache); git commit+push runs in a **background thread** (backup only)

CI has `paths-ignore` for `public/photos/**` + `public/manifest.json` → photo commits never trigger an image build; code changes still build + rollout as before. Rollback = revert nginx.conf aliases (baked copies still in image).

Auth = same `SITE_TOKEN` as chat; 15 MB cap; JPG/PNG/WebP/HEIC only. nginx `/api/` body limit 20m.

Known tradeoffs: photo serving depends on the Lima home mount (same dependency bookshelf carries); immutable cache can keep a deleted photo alive up to 1 year (deletion not in UI); originals (`src_photos/`) exist only on the Mac by choice.

## Repo

`~/GitHub/nuno-site` → github.com/immaribeiro/nuno-site · site https://nuno.immas.org (Cloudflare, PIN 6969).
