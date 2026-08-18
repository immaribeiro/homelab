#!/bin/bash
# Headless cron wrapper: download new e-books, then organize the library
# into Language/Author/ folders. Exit codes propagate honestly.
#   0 = success (download + organize), 1 = error, 2 = session needs --login

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENV_FILE="${TELEGRAM_ENV_FILE:-/Users/imma/.hermes/env/telegram-downloader.env}"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

PY="$DIR/.venv/bin/python"

# 1) Download (headless unless --login passed). Exits 2 if session missing.
"$PY" "$DIR/downloader.py" "$@"

# 2) Organize the library into author folders (idempotent; dedupes by MD5,
#    moves exact duplicates to _duplicates/).
"$PY" "$DIR/organize_library.py" --execute --dir "${TELEGRAM_DOWNLOAD_DIR:-/Users/imma/Downloads/ebook-library/PT}"
