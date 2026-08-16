#!/bin/bash
# serve-https.sh — Tailscale Serve status helper for Mission Control (port 9118).
#
# Prints the current `tailscale serve status`; if serve is not enabled, shows
# the one-time admin enable URL (account owner only) and the post-enable
# command. If enabled, prints the served URL. No destructive commands.
set -euo pipefail

PORT=9118
NODE_ID="njVGiA1tWh11CNTRL"
ENABLE_URL="https://login.tailscale.com/f/serve?node=${NODE_ID}"
SERVE_URL="https://imma-mini"

status_output="$(tailscale serve status 2>&1)"
echo "=== tailscale serve status ==="
echo "${status_output}"
echo

if echo "${status_output}" | grep -q "No serve config"; then
    echo "Tailscale Serve is NOT enabled for port ${PORT}."
    echo
    echo "One-time enable (admin console, account owner only):"
    echo "  ${ENABLE_URL}"
    echo
    echo "After enabling, start serving HTTPS:"
    echo "  tailscale serve --bg ${PORT}"
    echo
    echo "Resulting URL: ${SERVE_URL}"
else
    echo "Tailscale Serve is enabled for port ${PORT}:"
    echo "  ${SERVE_URL}"
fi
