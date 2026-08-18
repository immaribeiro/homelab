_Created: 2026-03-30_
§
Hermes config: hermes.json defines providers/models, config.yaml runtime settings — both must be updated for changes to take effect. API keys → .env, settings → config.yaml.
§
Mission Control: session observability app ~/GitHub/homelab/mission-control/ (:9118, launchd ai.hermes.mission-control, token ~/.hermes/mission-control/token, http://imma-mini:9118).
§
User works across multiple machines (Mac Mini as hub, Mac Air as client). Wants same Hermes sessions/memory/skills from any machine. NordVPN on Mac Mini conflicts with Tailscale — use LAN IP fallback or router-level VPN.
§
User wants implementation work split across configured Hermes profiles (architect/backend/frontend/engineer), each using its own configured model, skills, and memory — main agent orchestrates, reviews, integrates. Engineer profile has full autonomy on infra ops (start VMs, fix configs, deploy, restart services without asking).
§
K3s Lima cluster: VMs need `lima:shared` network + `--flannel-iface lima0`; on restart with new config, CA certs+node-token change — workers need the new token.
§
User's Hermes desktop app runs on the MacBook (connects to the Mini's gateway). The preview pane's 'localhost' is the MacBook's own loopback — for services on the Mini use tailnet hostnames/IPs (imma-mini, 100.101.63.91).
§
Telegram ebook downloader: ~/GitHub/homelab/telegram-downloader/ (Telethon downloader.py + run_downloader.sh = download→organize, recursive dedupe; creds ~/.hermes/env/telegram-downloader.env VALID). Channel -1002152949316 → ~/Downloads/ebook-library/PT, cron 17ed147e373f Sun 07:00. Library organized into ~272 author folders (~358 books, 11 in _duplicates/).
§
Bookshelf: e-book library web UI → books.immas.org. Plan: ~/GitHub/homelab/.hermes/plans/2026-08-18_075836-bookshelf-library.md. Repo ~/GitHub/bookshelf (FastAPI + React + OPDS for Kobo). Bookshelf owns library organization (organizer.py port, POST /api/organize, ORGANIZE_ON_SCAN, RW hostPath mount). Deploy: k8s/manifests/bookshelf.yml, ns books, ghcr.io/immaribeiro/bookshelf, tunnel route books.immas.org.