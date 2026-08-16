#!/usr/bin/env bash
set -euo pipefail
cd /Users/imma/GitHub/homelab/mission-control
exec /Users/imma/.hermes/hermes-agent/venv/bin/python -m backend.digest --days 1
