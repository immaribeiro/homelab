#!/bin/zsh
set -euo pipefail

# Automate Cloudflare Tunnel setup: detect existing tunnel, create if needed,
# capture UUID + credentials file path, and update .env variables.

TUNNEL_NAME_ARG=${1:-}
ENV_FILE=${ENV_FILE:-"${PWD}/.env"}

# Load existing .env if present to pick up predefined variables
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC2046
  set -a; source "${ENV_FILE}"; set +a
fi

# Prefer existing environment variables if defined
TUNNEL_NAME=${TUNNEL_NAME_ARG:-${CLOUDFLARE_TUNNEL_NAME:-homelab}}
TUNNEL_ID=${CLOUDFLARE_TUNNEL_ID:-""}
CRED_FILE_ENV=${CLOUDFLARE_TUNNEL_CRED_FILE:-""}
CLOUDFLARE_TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN:-""}

command -v cloudflared >/dev/null 2>&1 || {
  echo "Error: cloudflared CLI not found. Install from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" >&2
  exit 1
}

echo "Checking Cloudflare account access..."
if ! cloudflared tunnel list >/dev/null 2>&1; then
  echo "Cloudflare authentication required. Launching 'cloudflared login'..."
  cloudflared login
fi

if [[ -n "${TUNNEL_ID}" ]]; then
  echo "Using tunnel from .env: ${TUNNEL_NAME} (${TUNNEL_ID})"
else
  echo "Looking for existing tunnel named '${TUNNEL_NAME}'..."
  EXISTING_LINE=$(cloudflared tunnel list | awk -v name="${TUNNEL_NAME}" 'NR>1 && $2==name {print $0}' || true)
  if [[ -n "${EXISTING_LINE}" ]]; then
    TUNNEL_ID=$(echo "${EXISTING_LINE}" | awk '{print $1}')
    echo "Found existing tunnel: ${TUNNEL_NAME} (${TUNNEL_ID})"
  else
    echo "Creating new tunnel: ${TUNNEL_NAME}"
    cloudflared tunnel create "${TUNNEL_NAME}"
    TUNNEL_ID=$(cloudflared tunnel list | awk -v name="${TUNNEL_NAME}" 'NR>1 && $2==name {print $1}')
    if [[ -z "${TUNNEL_ID}" ]]; then
      echo "Error: Failed to detect the new tunnel ID for '${TUNNEL_NAME}'." >&2
      exit 1
    fi
    echo "Created tunnel: ${TUNNEL_NAME} (${TUNNEL_ID})"
  fi
fi

# Detect credentials file path in ~/.cloudflared, unless provided via .env
CRED_FILE=${CRED_FILE_ENV:-""}
if [[ -z "${CRED_FILE}" ]]; then
  CRED_FILE=$(ls -1 ~/.cloudflared/${TUNNEL_ID}.json 2>/dev/null | head -n1 || true)
fi
if [[ -z "${CRED_FILE}" ]]; then
  CRED_FILE=$(ls -1 ~/.cloudflared/*.json 2>/dev/null | grep "${TUNNEL_ID}" | head -n1 || true)
fi

if [[ -z "${CRED_FILE}" ]]; then
  echo "Error: Could not locate credentials file for tunnel ${TUNNEL_ID} in ~/.cloudflared" >&2
  echo "Hint: Ensure 'cloudflared tunnel create ${TUNNEL_NAME}' completed successfully." >&2
  exit 1
fi

echo "Using credentials file: ${CRED_FILE}"

# Update .env with Cloudflare variables (preserve existing names)
mkdir -p "${PWD}" >/dev/null 2>&1
touch "${ENV_FILE}"

update_env_var() {
  local key="$1"; local val="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i '' "s|^${key}=.*$|${key}=${val}|" "${ENV_FILE}"
  else
    echo "${key}=${val}" >> "${ENV_FILE}"
  fi
}

update_env_var CLOUDFLARE_TUNNEL_NAME "${TUNNEL_NAME}"
update_env_var CLOUDFLARE_TUNNEL_ID "${TUNNEL_ID}"
update_env_var CLOUDFLARE_TUNNEL_CRED_FILE "${CRED_FILE}"

# Preserve existing token if present; otherwise leave empty (token is for dashboard-managed flows)
if [[ -n "${CLOUDFLARE_TUNNEL_TOKEN}" ]]; then
  update_env_var CLOUDFLARE_TUNNEL_TOKEN "${CLOUDFLARE_TUNNEL_TOKEN}"
fi

echo "Updated ${ENV_FILE} with:"
echo "  CLOUDFLARE_TUNNEL_NAME=${TUNNEL_NAME}"
echo "  CLOUDFLARE_TUNNEL_ID=${TUNNEL_ID}"
echo "  CLOUDFLARE_TUNNEL_CRED_FILE=${CRED_FILE}"
[[ -n "${CLOUDFLARE_TUNNEL_TOKEN}" ]] && echo "  CLOUDFLARE_TUNNEL_TOKEN=<preserved>"

echo "Creating/refreshing Kubernetes secret cloudflared-credentials in namespace cloudflared..."
kubectl create namespace cloudflared --dry-run=client -o yaml | kubectl apply -f -
kubectl -n cloudflared delete secret cloudflared-credentials --ignore-not-found
kubectl -n cloudflared create secret generic cloudflared-credentials --from-file=tunnel.json="${CRED_FILE}"

echo "Done. Now set 'tunnel:' in k8s/cloudflared/tunnel.yaml to ${TUNNEL_ID} and apply:"
echo "  kubectl apply -f k8s/cloudflared/tunnel.yaml"
