#!/usr/bin/env bash
# Hermes state DB backup wrapper (daily, via launchd job ai.hermes.backup).
# Runs backup-hermes.py (passing -n/--dry-run through), then prunes
# backups older than 14 days. Non-zero exits from the python script are
# preserved (set -e stops the wrapper immediately, so no pruning happens
# after a failed backup).
set -euo pipefail

SCRIPT="/Users/imma/.hermes/scripts/backup-hermes.py"
BACKUP_DIR="/Users/imma/Backups/hermes"
LOG_DIR="${HOME}/.hermes/logs"
LOG_FILE="${LOG_DIR}/backup.log"

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        -n|--dry-run) DRY_RUN=1 ;;
    esac
done

mkdir -p "${LOG_DIR}"

{
    echo "===== hermes backup $(date '+%Y-%m-%d %H:%M:%S %Z') (dry_run=${DRY_RUN}) ====="
    /usr/bin/python3 "${SCRIPT}" "$@"
    if [ "${DRY_RUN}" -eq 0 ]; then
        if [ -d "${BACKUP_DIR}" ]; then
            find "${BACKUP_DIR}" -type f -name 'hermes-*.sqlite.gz' -mtime +14 -print -delete
            echo "pruned backups older than 14 days"
        fi
    fi
    echo "===== done ====="
} >> "${LOG_FILE}" 2>&1
