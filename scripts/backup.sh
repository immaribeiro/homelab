#!/bin/zsh
set -euo pipefail

OUT_DIR=${1:-backups/$(date +%Y%m%d-%H%M%S)}
mkdir -p "$OUT_DIR"
echo "[backup] Output directory: $OUT_DIR"

echo "[backup] Detecting pods"
HA_POD=$(kubectl -n home-assistant get pod -l app=home-assistant -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
PLEX_POD=$(kubectl -n plex get pod -l app=plex -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

if [ -z "$HA_POD" ]; then echo "[backup] Home Assistant pod not found"; else
  echo "[backup] Copying Home Assistant /config from $HA_POD"
  kubectl -n home-assistant cp "$HA_POD:/config" "$OUT_DIR/home-assistant-config" || echo "[backup] WARN: Failed to copy Home Assistant config"
fi

if [ -z "$PLEX_POD" ]; then echo "[backup] Plex pod not found"; else
  echo "[backup] Copying Plex /config from $PLEX_POD"
  kubectl -n plex cp "$PLEX_POD:/config" "$OUT_DIR/plex-config" || echo "[backup] WARN: Failed to copy Plex config"
fi

echo "[backup] Creating tarballs"
if [ -d "$OUT_DIR/home-assistant-config" ]; then
  tar -czf "$OUT_DIR/home-assistant-config.tgz" -C "$OUT_DIR" home-assistant-config && rm -rf "$OUT_DIR/home-assistant-config"
fi
if [ -d "$OUT_DIR/plex-config" ]; then
  tar -czf "$OUT_DIR/plex-config.tgz" -C "$OUT_DIR" plex-config && rm -rf "$OUT_DIR/plex-config"
fi

echo "[backup] Done. Files:"
ls -lh "$OUT_DIR"