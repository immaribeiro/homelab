#!/bin/bash
# Headless cron wrapper: download from all configured chats, then organize
# each language library into author folders.
#   0 = success, 1 = configuration/runtime error, 2 = session needs --login

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENV_FILE="${TELEGRAM_ENV_FILE:-/Users/imma/.hermes/env/telegram-downloader.env}"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

PY="$DIR/.venv/bin/python"
DOWNLOAD_ROOT="${TELEGRAM_DOWNLOAD_ROOT:-}"
if [[ -z "$DOWNLOAD_ROOT" ]]; then
    # TELEGRAM_DOWNLOAD_DIR was historically the PT directory. Treat it as
    # the library root when it already names the root, otherwise use its
    # parent so this wrapper can create both PT/ and ENG/ below it.
    LEGACY_DIR="${TELEGRAM_DOWNLOAD_DIR:-/Users/imma/Downloads/ebook-library/PT}"
    if [[ "$(basename "$LEGACY_DIR")" == "PT" || "$(basename "$LEGACY_DIR")" == "ENG" ]]; then
        DOWNLOAD_ROOT="$(dirname "$LEGACY_DIR")"
    else
        DOWNLOAD_ROOT="$LEGACY_DIR"
    fi
fi

# A comma- or newline-separated list is accepted for each language. The
# unqualified variable remains a backwards-compatible alias for PT.
PT_CHATS="${TELEGRAM_PT_TARGET_CHATS:-${TELEGRAM_TARGET_CHATS_PT:-${TELEGRAM_TARGET_CHATS:-}}}"
ENG_CHATS="${TELEGRAM_ENG_TARGET_CHATS:-${TELEGRAM_TARGET_CHATS_ENG:-}}"

overall_status=0
login_done=0
login_requested=0
for arg in "$@"; do
    [[ "$arg" == "--login" ]] && login_requested=1
done
DOWNLOADER_ARGS=("$@")

record_status() {
    local status="$1"
    if (( status == 2 )); then
        overall_status=2
    elif (( status != 0 && overall_status == 0 )); then
        overall_status=1
    fi
}

run_group() {
    local language="$1"
    local raw_chats="$2"
    local language_dir="$DOWNLOAD_ROOT/$language"
    local chat chat_status
    local -a chats

    # Make newline-separated values behave like comma-separated values.
    raw_chats="${raw_chats//$'\n'/,}"
    IFS=',' read -r -a chats <<< "$raw_chats"

    for chat in "${chats[@]}"; do
        # Trim leading/trailing whitespace without invoking external tools.
        chat="${chat#"${chat%%[![:space:]]*}"}"
        chat="${chat%"${chat##*[![:space:]]}"}"
        [[ -z "$chat" ]] && continue

        # Login creates one shared session; do not prompt once per chat.
        if (( login_done )); then
            continue
        fi

        printf '[info] downloading %s chat %s into %s\n' "$language" "$chat" "$language_dir"
        set +e
        TELEGRAM_TARGET_CHATS="$chat" \
        TELEGRAM_DOWNLOAD_DIR="$language_dir" \
            "$PY" "$DIR/downloader.py" "${DOWNLOADER_ARGS[@]}"
        chat_status=$?
        set -e
        record_status "$chat_status"

        if (( login_requested )); then
            login_done=1
        fi
    done

    # Organize even when one chat failed, so successful chats and prior runs
    # still get processed. The final status reports any downloader failure.
    printf '[info] organizing %s library at %s\n' "$language" "$language_dir"
    set +e
    "$PY" "$DIR/organize_library.py" --execute --dir "$language_dir"
    chat_status=$?
    set -e
    record_status "$chat_status"
}

# Pass all wrapper arguments through to downloader.py for every chat.
run_group PT "$PT_CHATS"
run_group ENG "$ENG_CHATS"

exit "$overall_status"
