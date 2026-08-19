_Created: 2026-03-30_
§
Hermes config: hermes.json = providers/models, config.yaml = settings; API keys → .env. `hermes config set` mangles list values — patch config.yaml surgically. Gateway restart applies config changes.
§
Mission Control: dashboard ~/GitHub/homelab/mission-control/ (:9118, launchd ai.hermes.mission-control, token ~/.hermes/mission-control/token, http://imma-mini:9118). Aggregates all profile state DBs; lease-guarded session mgmt.
§
Multi-machine: Mac Mini = hub (imma-mini; LAN 192.168.8.161, tailnet 100.101.63.91), MacBook = client. NordVPN on Mini breaks Tailscale — use LAN fallback; 'localhost' preview = MacBook loopback.
§
Profiles: main + architect/backend/frontend/engineer/researcher; main orchestrates/reviews/integrates. Engineer: full autonomy on infra. Researcher: deep research.
§
K3s Lima: VMs need `lima:shared` net + `--flannel-iface lima0`; config changes rotate CA certs/node-token — rejoin workers.
§
Telegram ebook downloader: ~/GitHub/homelab/telegram-downloader/ (Telethon downloader.py + run_downloader.sh; creds ~/.hermes/env/telegram-downloader.env). Channel -1002152949316 → ~/Downloads/ebook-library/PT, cron 17ed147e373f Sun 07:00. ~272 author folders.
§
Uploads: k3s-worker-1 staging → bookshelf-upload-sync.sh (launchd, 3min) → PT/ + rescan. Lima mounts Mac home RO (in-cluster writes 409); pod pinned k3s-worker-1.
§
Researcher profile (deep research): skills from ~/GitHub/awesome-llm-apps; Telegram 🔬 thread 431 (tg-researcher).
§
nuno-site chat: nuno-chat-bridge (homelab repo; launchd ai.hermes.nuno-chat-bridge :8643) relays site /api/ → Hermes API server 127.0.0.1:8642 (gateway.api_server in config.yaml; keys in ~/.hermes/env/nuno-chat-bridge.env + src/config.js). Conversation 'nuno-site'.