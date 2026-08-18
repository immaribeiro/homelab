#!/bin/bash
# bookshelf-upload-sync.sh — pull Bookshelf UI uploads from the cluster staging dir
# into the e-book library, then run the organizer (idempotent, 0 moves when stable).
# Runs every 3 min via launchd (ai.hermes.bookshelf-upload-sync).
# The Lima VMs mount the Mac home read-only, so in-cluster writes are impossible;
# the app stages uploads on the VM's own disk and this script moves them in.

NODE=k3s-worker-1
STAGE=/home/imma.linux/bookshelf-uploads
DEST=${BOOKSHELF_LIBRARY_DIR:-/Users/imma/Downloads/ebook-library/PT}
LOG=${BOOKSHELF_SYNC_LOG:-/tmp/bookshelf-upload-sync.log}
ORG_DIR=/Users/imma/GitHub/homelab/telegram-downloader
LIMACTL=${LIMACTL:-/opt/homebrew/bin/limactl}

moved=0
while IFS= read -r -d '' f; do
  name=$(basename "$f")
  if "$LIMACTL" shell "$NODE" cat "$STAGE/$name" > "$DEST/$name" 2>>"$LOG"; then
    "$LIMACTL" shell "$NODE" rm -f "$STAGE/$name" 2>>"$LOG"
    moved=$((moved + 1))
    echo "$(date '+%F %T') moved: $name" >> "$LOG"
  else
    echo "$(date '+%F %T') FAILED: $name" >> "$LOG"
  fi
done < <("$LIMACTL" shell "$NODE" find "$STAGE" -maxdepth 1 -type f -print0 2>>"$LOG" || true)

if [ "$moved" -gt 0 ]; then
  echo "$(date '+%F %T') synced $moved file(s); organizing…" >> "$LOG"
  (cd "$ORG_DIR" && .venv/bin/python organize_library.py --execute --dir "$DEST") >> "$LOG" 2>&1 || \
    echo "$(date '+%F %T') organizer failed" >> "$LOG"
fi
exit 0
