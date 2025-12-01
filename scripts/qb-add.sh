#!/usr/bin/env bash
set -euo pipefail

# qb-add.sh — Add a magnet link to qBittorrent via WebUI API
# Usage:
#   scripts/qb-add.sh 'magnet:?xt=urn:btih:...' [--savepath /downloads] [--host https://qb.immas.org] [--user admin] [--pass ******]
#
# Notes:
# - Requires qBittorrent WebUI reachable at --host
# - Uses HTTPS headers (Referer/Origin) to satisfy CSRF/WAF
# - Credentials can be set via env QB_USER/QB_PASS/QB_HOST or flags

HOST="${QB_HOST:-https://qb.immas.org}"
USER="${QB_USER:-admin}"
PASS="${QB_PASS:-xopnad-pyzti1-Xybvop}"
SAVEPATH=""
MAGNET=""

usage() {
  echo "Usage: $0 'magnet:?xt=urn:btih:...' [--savepath /downloads] [--host https://qb.immas.org] [--user admin] [--pass ******]" >&2
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --savepath)
      SAVEPATH="${2:-}"; shift 2 ;;
    --host)
      HOST="${2:-}"; shift 2 ;;
    --user)
      USER="${2:-}"; shift 2 ;;
    --pass)
      PASS="${2:-}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      if [[ -z "$MAGNET" ]]; then
        MAGNET="$1"; shift
      else
        echo "Unexpected argument: $1" >&2; usage; exit 2
      fi ;;
  esac
done

if [[ -z "$MAGNET" ]]; then
  echo "Error: magnet link is required" >&2
  usage
  exit 2
fi

# Basic validation
if [[ "$MAGNET" != magnet:* ]]; then
  echo "Error: argument does not look like a magnet link" >&2
  exit 2
fi

# Normalize host (strip trailing slash)
HOST="${HOST%/}"
API_LOGIN="$HOST/api/v2/auth/login"
API_VERSION="$HOST/api/v2/app/version"
API_ADD="$HOST/api/v2/torrents/add"

COOKIES_FILE="$(mktemp -t qb_cookies.XXXXXX)"
cleanup() { rm -f "$COOKIES_FILE" 2>/dev/null || true; }
trap cleanup EXIT

# 1) Login
LOGIN_RESP=$(curl -sS -w "%{http_code}" -o /dev/null -c "$COOKIES_FILE" \
  -d "username=$USER&password=$PASS" "$API_LOGIN")
if [[ "$LOGIN_RESP" != "200" ]]; then
  echo "Login failed (HTTP $LOGIN_RESP). Check HOST/USER/PASS." >&2
  exit 1
fi

# 2) Optional: verify session
curl -sS -b "$COOKIES_FILE" "$API_VERSION" >/dev/null || {
  echo "Warning: Could not verify session version endpoint" >&2
}

# 3) Add torrent (send Referer/Origin for CSRF/WAF)
curl -sS -b "$COOKIES_FILE" \
  -H "Referer: ${HOST}/" \
  -H "Origin: ${HOST}" \
  -d "urls=${MAGNET}" \
  ${SAVEPATH:+-d "savepath=${SAVEPATH}"} \
  ${SAVEPATH:+-d "autoTMM=false"} \
  "$API_ADD"

echo
echo "✓ Submitted magnet to qBittorrent at $HOST"
