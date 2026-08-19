# Nuno Site (nuno.immas.org)

Private couple site for Imma + Nuno. Static Vite + React + Tailwind v3, deployed to K3s (namespace `nuno`), CI via GitHub Actions → ghcr → manual rollout.

## Pages

1. **The archive** — photo gallery (manifest.json / photos/).
2. **Events** — Porto/Braga cultural events, prices, jazz/fado focus chips, star pins (personal + shared `pinned.json`).
3. **News** — 5 categories (Portugal / Porto & Braga / Mundo / Música / IA), addable topics, quotas per category.
4. **Us** — weather (Open-Meteo), days-together counter, date-ideas bucket list (🎲 Surpresa), milestones, songs. Config: `public/couple.json`.
5. **Hermes** — direct chat with the assistant (see below).

## Pipelines (daily 06:00, `~/.hermes/scripts/events-fetch.sh`)

- `fetch_events.py` → `public/events.json` (venues + Eventbrite browse-page scraping, keyless, price enrichment from detail pages).
- **Curated events**: hand-picked calendar entries live in `MANUAL_EVENTS` inside `fetch_events.py` — they survive the daily refresh and bypass the 14-day window (shown as soon as marked). Used e.g. for Verde Cool (Braga, 7 set–4 out).
- `fetch_news.py` → `public/news.json` (stdlib RSS/Atom, quotas, idempotent).
- Only commits+pushes on change → CI builds image → `kubectl rollout restart deployment/nuno-site -n nuno`.

## Chat with Hermes

Browser → Cloudflare → K3s nginx → `/api/` upstream (dual-IP failover) → **nuno-chat-bridge** on the hub (launchd `ai.hermes.nuno-chat-bridge`, :8643) → **Hermes API server** (:8642, inside the gateway, enabled via `gateway.api_server` in `~/.hermes/config.yaml`) → agent session `nuno-site`.

- Secrets: `~/.hermes/env/nuno-chat-bridge.env` (chmod 600) — `HERMES_API_KEY` == `API_SERVER_KEY`, `SITE_TOKEN` == `SITE_TOKEN` in `src/config.js`.
- Code + docs: `~/GitHub/homelab/nuno-chat-bridge/`.
- Bridge reply path verified by `restart-and-verify.sh` (one-shot launchd job, reports to Telegram).

## Repo

`~/GitHub/nuno-site` → github.com/immaribeiro/nuno-site · site https://nuno.immas.org (Cloudflare, PIN 6969).
