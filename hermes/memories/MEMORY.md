_Created: 2026-03-30_
§
Hermes config: hermes.json = providers/models, config.yaml = settings; API keys → .env. `hermes config set` mangles list values (stores as JSON string) — patch config.yaml surgically instead. Route/model changes need gateway restart from a shell outside the gateway.
§
Mission Control: session dashboard ~/GitHub/homelab/mission-control/ (:9118, launchd ai.hermes.mission-control, token ~/.hermes/mission-control/token, http://imma-mini:9118). Aggregates ALL profile state DBs; session mgmt (archive/delete lease-guarded, hanging filter, sort, pagination).
§
Multi-machine: Mac Mini = hub (imma-mini, 192.168.8.161, 100.101.63.91), MacBook = client (desktop app → Mini gateway). NordVPN on Mini conflicts with Tailscale — use LAN IP fallback. 'localhost' preview = MacBook loopback; use tailnet hostnames (imma-mini) for Mini services.
§
Profiles: main + architect/backend/frontend/engineer/researcher, own model/skills/memory; main orchestrates/reviews/integrates. Engineer full autonomy on infra ops. Researcher = deep research (deepseek-v4-flash + glm-5.2).
§
K3s Lima cluster: VMs need `lima:shared` network + `--flannel-iface lima0`; on restart with new config, CA certs+node-token change — workers need the new token.
§
Telegram ebook downloader: ~/GitHub/homelab/telegram-downloader/ (Telethon downloader.py + run_downloader.sh; creds ~/.hermes/env/telegram-downloader.env). Channel -1002152949316 → ~/Downloads/ebook-library/PT, cron 17ed147e373f Sun 07:00. ~272 author folders.
§
Bookshelf: e-book library UI at https://books.immas.org (ns books, ghcr.io/immaribeiro/bookshelf via GH Actions CI — Mini Docker can't pull). Repo ~/GitHub/bookshelf (FastAPI+React+OPDS/Kobo + epub.js). Users imma+joaoreis, pw in secret bookshelf-auth. Uploads staged k3s-worker-1 → homelab/scripts/bookshelf-upload-sync.sh (launchd ai.hermes.bookshelf-upload-sync, 3min) → PT/ + rescan. Lima mounts Mac home RO → in-cluster writes 409; pod pinned k3s-worker-1.
§
awesome-llm-apps cloned ~/GitHub/awesome-llm-apps (Apache-2.0) — skills source (see skills_list). Researcher profile: deep-research-patterns/llm-memory-patterns/token-optimization; Telegram 🔬 thread 431 (tg-researcher).