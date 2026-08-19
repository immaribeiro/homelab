_Created: 2026-03-30_
§
Hermes config: hermes.json = providers/models, config.yaml = settings; API keys → .env. `hermes config set` mangles list values — patch config.yaml surgically. Gateway restart applies config changes.
§
Mission Control: dashboard ~/GitHub/homelab/mission-control/ (:9118, launchd ai.hermes.mission-control, token ~/.hermes/mission-control/token, http://imma-mini:9118). Aggregates all profile state DBs; lease-guarded session mgmt.
§
Multi-machine: Mac Mini = hub (imma-mini; LAN 192.168.8.161, tailnet 100.101.63.91), MacBook = client. NordVPN on Mini breaks Tailscale — use LAN fallback; 'localhost' preview = MacBook loopback.
§
Investor (2026-08-19): Revolut X MCP (~/GitHub/revolut-x-api, 22 tools) + finance skills; cron 07:30 briefing + Sat review + 15-min watchdog; journal ~/GitHub/homelab/investor/; Marketaux in investor .env (param api_token=, not token=); TG tg-investor → thread 1016 LIVE (restarted 08-19); REVX creds ~/.config/revolut-x/config.json (PITFALL: MCP ignores REVX_* env vars; 0600/0700 perms); Trading 212 account created — awaiting API key+secret (Settings→API Beta→Generate; Basic auth API_KEY:API_SECRET; demo/live .trading212.com/api/v0).
§
K3s Lima: VMs need `lima:shared` net + `--flannel-iface lima0`; config changes rotate CA certs/node-token — rejoin workers.
§
Telegram ebook downloader: ~/GitHub/homelab/telegram-downloader/ (Telethon downloader.py + run_downloader.sh; creds ~/.hermes/env/telegram-downloader.env). Channel -1002152949316 → ~/Downloads/ebook-library/PT, cron 17ed147e373f Sun 07:00. ~272 author folders.
§
Uploads: k3s-worker-1 staging → bookshelf-upload-sync.sh (launchd, 3min) → PT/ + rescan. Lima mounts Mac home RO (in-cluster writes 409); pod pinned k3s-worker-1.
§
Researcher profile (deep research): skills from ~/GitHub/awesome-llm-apps; Telegram 🔬 thread 431 (tg-researcher).
§
nuno-site: chat via nuno-chat-bridge (homelab; launchd :8643) → Hermes API 127.0.0.1:8642, session 'nuno-site'. Curated calendar events = MANUAL_EVENTS in fetch_events.py (survive 06:00 refresh). Deploy: push → GH Actions → ghcr → kubectl rollout restart deployment/nuno-site -n nuno.