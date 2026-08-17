#!/bin/bash
# Headless cron wrapper for downloader.py.
# Sources the external env file, then execs the script so its exit code
# propagates honestly to the scheduler.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENV_FILE="${TELEGRAM_ENV_FILE:-/Users/imma/.hermes/env/telegram-downloader.env}"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

PY="$DIR/.venv/bin/python"

exec "$PY" "$DIR/downloader.py" "$@"
