_Created: 2026-03-30_
§
Hermes config: hermes.json = providers/models, config.yaml = settings; API keys → .env. `hermes config set` mangles list values — patch config.yaml surgically. Gateway restart applies config changes.
§
Mission Control: dashboard ~/GitHub/homelab/mission-control/ (:9118, launchd ai.hermes.mission-control, token ~/.hermes/mission-control/token, http://imma-mini:9118). Aggregates all profile state DBs; lease-guarded session mgmt.
§
Multi-machine: Mac Mini = hub (imma-mini; LAN 192.168.8.161, tailnet 100.101.63.91), MacBook = client. NordVPN on Mini breaks Tailscale — use LAN fallback; 'localhost' preview = MacBook loopback.
§
TG tg-investor thread 1016 LIVE
§
K3s Lima: VMs need `lima:shared` net + `--flannel-iface lima0`; config changes rotate CA certs/node-token — rejoin workers.
§
Telegram ebook downloader: ~/GitHub/homelab/telegram-downloader/ (downloader.py + run_downloader.sh; creds ~/.hermes/env/telegram-downloader.env). ONE forum channel Floresta Encantada -1002152949316, topic-scoped: PT topic 3 → ~/Downloads/ebook-library/PT (371 files/1.3GB), ENG topic 5 → ENG/ (484 files/1.1GB, backfilling 1GiB/Sun). Cron 17ed147e373f Sun 07:00.
§
Uploads: k3s-worker-1 staging → bookshelf-upload-sync.sh (launchd 3min) → PT/ + rescan. Lima mounts Mac home RO; pod pinned k3s-worker-1.
§
Researcher: skills from ~/GitHub/awesome-llm-apps; Telegram 🔬 thread 431 (tg-researcher).
§
Upload: /api/upload → pipeline.py → live via hostPath mount /mnt/photos (no rebuild, ~0.3s; nginx aliases /photos/ + /manifest.json); git backup async; CI paths-ignore photos.