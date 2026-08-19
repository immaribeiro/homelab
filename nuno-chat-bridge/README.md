# nuno-chat-bridge

Thin authenticated relay that gives **nuno.immas.org** a direct line to the
Hermes assistant (Imma's personal AI agent) — so Nuno can ask for anything
from inside the site: new news topics, event suggestions, changes to the Us
page, or whatever else.

## Architecture

```
Browser (nuno.immas.org)
  → Cloudflare
  → K3s ingress → nuno-site nginx (static site)
  → location /api/  (nginx.conf `upstream hermes_bridge`, dual-IP failover)
  → this bridge (host, :8643, launchd `ai.hermes.nuno-chat-bridge`)
  → Hermes API server (127.0.0.1:8642, inside the Hermes gateway)
  → agent session "nuno-site" (full tools + memory, replies in PT-PT)
```

Multi-turn conversations use the API server's named `conversation` (default
`nuno-site`) — they appear in the Hermes dashboard like any other session.

## Security model

- The **Hermes API key never leaves this machine**. The site only holds a weak
  client-side token (`SITE_TOKEN` in `src/config.js`); the bridge validates it
  with a constant-time compare and holds the real key.
- Rate limiting: per-IP sliding window (20/hour) + 300/day global cap.
- Message length capped at 2000 chars; plain text to the LLM only (no shell,
  no HTML). The assistant itself is the safety gate on actions.
- Photo uploads (`POST /api/upload`) use the same token gate; files are
  validated (JPG/PNG/WebP/HEIC, ≤ 15 MB) before the pipeline touches them.

## Endpoints

- `POST /api/chat` — relay a message to the Hermes agent session (`nuno-site`).
- `POST /api/upload` — accept a photo (multipart field `file`), save it to
  `~/GitHub/nuno-site/src_photos/`, run the site's `pipeline.py` (WebP
  optimization + manifest regeneration), then `git commit` + `git push` —
  GitHub Actions rebuilds the image, GHCR gets a new `latest`, and the
  `ghcr-deploy-watch` launchd job rolls the k3s Deployment. Photo appears on
  the site a few minutes later. Same `SITE_TOKEN` auth as chat.

## Files

- `bridge.py` — FastAPI app (runs on the hermes-agent venv python; fastapi/uvicorn/httpx).
- `restart-and-verify.sh` + `com.imma.nuno-bridge-restart-verify.plist` —
  one-shot: restarts the gateway so it picks up `API_SERVER_*` env vars, then
  verifies bridge → API server end-to-end and reports to Telegram.
- `~/Library/LaunchAgents/ai.hermes.nuno-chat-bridge.plist` — service plist
  (KeepAlive, logs to `~/.hermes/logs/nuno-chat-bridge*.log`).
- `~/.hermes/env/nuno-chat-bridge.env` (chmod 600) — secrets:
  `HERMES_API_URL`, `HERMES_API_KEY` (== `API_SERVER_KEY` in `~/.hermes/.env`),
  `SITE_TOKEN` (== `SITE_TOKEN` in the site's `src/config.js`),
  `CHAT_CONVERSATION`, `RATE_LIMIT_PER_IP`.

## Enable / restart

```bash
# Hermes config.yaml: gateway.api_server { enabled: true, port: 8642, host: 127.0.0.1, key: <API_SERVER_KEY> }
launchctl load -w ~/Library/LaunchAgents/ai.hermes.nuno-chat-bridge.plist   # start bridge
launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway                        # restart gateway
curl http://127.0.0.1:8642/health                                            # API server up?
curl http://127.0.0.1:8643/health                                            # bridge up?
```

## Test

```bash
curl -X POST http://127.0.0.1:8643/api/chat \
  -H "Authorization: Bearer $SITE_TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"Olá, Hermes!"}'
```
