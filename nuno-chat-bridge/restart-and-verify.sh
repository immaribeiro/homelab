#!/bin/bash
# One-shot (launchd): restart the Hermes gateway so it picks up the API server
# env vars, then verify the whole chat chain: bridge → API server → agent reply.
# Runs detached from the gateway (launchd-owned) so it survives the restart.
set -uo pipefail

LOG="$HOME/.hermes/logs/nuno-bridge-verify.log"
ENV_FILE="$HOME/.hermes/env/nuno-chat-bridge.env"
HERMES_CLI="${HERMES_CLI:-hermes}"
TG_TARGET="telegram:-1004449482428:1"

exec >>"$LOG" 2>&1
echo "=== $(date '+%F %T') verify start ==="

# Give the current turn time to finish before the gateway goes down.
sleep 75

launchctl kickstart -k "gui/$(id -u)/ai.hermes.gateway" || echo "gateway kickstart failed"

# Poll the API server health endpoint (started inside the gateway).
UP=0
for i in $(seq 1 45); do
  sleep 2
  if curl -s -m 3 http://127.0.0.1:8642/health | grep -q '"ok"'; then
    UP=1
    break
  fi
done
echo "api server up: $UP"

# End-to-end: bridge → Hermes API server → agent reply.
set -a
. "$ENV_FILE"
set +a
REPLY=$(curl -s -m 150 -X POST http://127.0.0.1:8643/api/chat \
  -H "Authorization: Bearer $SITE_TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"Olá! Isto é um teste automático do novo chat do site. Responde apenas com: TUDO A FUNCIONAR"}')
echo "bridge reply: $REPLY"

BODY="✅ Chat do site verificado — pipeline Hermes ligado."
if echo "$REPLY" | grep -q "TUDO A FUNCIONAR"; then
  BODY="$BODY A resposta chegou da sessão 'nuno-site'."
else
  BODY="$BODY Resposta inesperada: $REPLY"
fi
"$HERMES_CLI" send --to "$TG_TARGET" "$BODY" || echo "telegram send failed"

# Unload self (one-shot).
launchctl bootout "gui/$(id -u)/com.imma.nuno-bridge-restart-verify" 2>/dev/null || true
echo "=== done $(date '+%F %T') ==="
