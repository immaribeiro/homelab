#!/bin/bash
# ============================================================================
# ghcr-deploy-watch.sh — auto-deploy watcher: GHCR :latest → K3s rollouts
#
# Closes the CI-to-k8s gap: GitHub Actions pushes new images to GHCR tagged
# `latest`, but Deployments pin `image: ...:latest` and never re-pull until a
# manual `kubectl rollout restart`. This watcher (launchd, every 180s) resolves
# the GHCR `latest` manifest digest, compares it to the digest each running pod
# actually has, and restarts the Deployment when they differ — K3s/containerd
# then re-pulls `:latest` because the tag now points at a new digest.
#
# Config: one entry per line in APPS — "deployment_name|namespace|ghcr_image:tag"
#   Pods are matched with `-l app=<deployment_name>` (the label convention used
#   by every deployment in this homelab); override by adding a 4th selector
#   field (e.g. "bookshelf|books|ghcr.io/...:latest|app=bookshelf").
#
# Modes:
#   (no args)  watch mode — quiet stdout; only appends action lines to $LOG.
#   --check    print GHCR vs running digest + verdict per app; NO cluster changes.
#
# Digest sources (tried in order):
#   1. GitHub REST API — gh api user|orgs/<owner>/packages/container/<name>/versions
#      CAVEAT (verified Aug 2026): for images pushed by build-push-action with
#      provenance, GitHub returns .metadata.container.digest = null in both the
#      listing and the per-version detail endpoint. Observed for BOTH homelab
#      packages, so this path usually yields nothing and we fall through to (2).
#   2. GHCR registry manifest HEAD with a token from ghcr.io/token exchange
#      (basic auth using the `gh auth token` OAuth token — works for private
#      packages; anonymous 401s). The Docker-Content-Digest response header is
#      the digest of the `latest` manifest. This is the effective primary path.
#      (skopeo/oras are NOT installed on this Mac; curl + token exchange was
#      verified working — that is the documented "manifest inspect" fallback.)
#   3. Last resort — docker buildx imagetools inspect <image> --format '{{.Manifest.Digest}}'
#
# Assumption: the registry digest returned for the `latest` tag equals the
# running pod's imageID digest (verified empirically for both apps — containerd
# stores the manifest digest as imageID). If a future image is multi-arch and
# the pod resolves to a per-platform manifest, imageID may differ from the
# index digest; the watcher would then restart once per image push.
# ============================================================================

set -euo pipefail

APPS=(
  "bookshelf|books|ghcr.io/immaribeiro/bookshelf:latest"
  "reconstruction-app|reconstruction-app|ghcr.io/immaribeiro/reconstruction-app:latest"
)

LOG="${GHCR_WATCH_LOG:-/Users/imma/.hermes/logs/ghcr-deploy-watch.log}"
GH=${GH:-/opt/homebrew/bin/gh}
KUBECTL=${KUBECTL:-/usr/local/bin/kubectl}
CURL=${CURL:-/usr/bin/curl}
JQ=${JQ:-/usr/bin/jq}

MODE=watch
[ "${1:-}" = "--check" ] && MODE=check

log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

# --- resolve the digest the `latest` tag currently points at ----------------
# usage: ghcr_digest <owner> <name> <tag>   -> prints sha256:... on stdout
ghcr_digest() {
  local owner=$1 name=$2 tag=$3 d="" login=""
  login=$("$GH" api user --jq .login 2>/dev/null || true)

  # 1) GitHub REST API (user namespace, or org namespace for non-user owners)
  if [ -n "$login" ]; then
    if [ "$owner" = "$login" ]; then
      d=$("$GH" api "user/packages/container/${name}/versions" --paginate \
          --jq ".[] | select(.metadata.container.tags | index(\"${tag}\")) | .metadata.container.digest" \
          2>/dev/null | head -1 || true)
    else
      d=$("$GH" api "orgs/${owner}/packages/container/${name}/versions" --paginate \
          --jq ".[] | select(.metadata.container.tags | index(\"${tag}\")) | .metadata.container.digest" \
          2>/dev/null | head -1 || true)
    fi
  fi
  if [ -n "$d" ]; then printf '%s\n' "$d"; return 0; fi

  # 2) GHCR token exchange + manifest HEAD (the working path — see header)
  local ghtoken rt
  ghtoken=$("$GH" auth token 2>/dev/null || true)
  if [ -n "$ghtoken" ]; then
    rt=$("$CURL" -fsS -u "${owner}:${ghtoken}" \
        "https://ghcr.io/token?scope=repository:${owner}/${name}:pull&service=ghcr.io" \
        2>/dev/null | "$JQ" -r '.token // empty' 2>/dev/null || true)
    if [ -n "$rt" ]; then
      d=$("$CURL" -fsSI -H "Authorization: Bearer ${rt}" \
          -H "Accept: application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json" \
          "https://ghcr.io/v2/${owner}/${name}/manifests/${tag}" 2>/dev/null \
          | awk -F': ' 'tolower($1)=="docker-content-digest" {gsub("\r","",$2); print $2; exit}' || true)
    fi
  fi
  if [ -n "$d" ]; then printf '%s\n' "$d"; return 0; fi

  # 3) docker buildx imagetools (last resort)
  if command -v docker >/dev/null 2>&1; then
    d=$(docker buildx imagetools inspect "ghcr.io/${owner}/${name}:${tag}" --format '{{.Manifest.Digest}}' 2>/dev/null || true)
  fi
  if [ -n "$d" ]; then printf '%s\n' "$d"; return 0; fi
  return 1
}

# --- cluster must be reachable; skip silently during a reboot ---------------
if ! "$KUBECTL" get node >/dev/null 2>&1; then
  if [ "$MODE" = check ]; then
    echo "ERROR: cluster unreachable (kubectl get node failed)"
    exit 1
  fi
  exit 0
fi

rc=0
for entry in "${APPS[@]}"; do
  IFS='|' read -r dep ns img sel <<< "$entry"
  sel="${sel:-app=${dep}}"

  local_path="${img#ghcr.io/}"          # strip registry prefix
  owner="${local_path%%/*}"
  rest="${local_path#*/}"
  name="${rest%%:*}"
  tag="${rest#*:}"; [ "$tag" = "$rest" ] && tag=latest

  gd=""; gd=$(ghcr_digest "$owner" "$name" "$tag" || true)
  gd="${gd#sha256:}"   # normalize: registry returns sha256:... ; imageID is bare

  imageid=$("$KUBECTL" -n "$ns" get pod -l "$sel" -o jsonpath='{.items[0].status.containerStatuses[0].imageID}' 2>/dev/null || true)
  running=""
  if [ -n "$imageid" ]; then
    running="${imageid##*@sha256:}"
    [ "$running" = "$imageid" ] && running=""
  fi

  if [ "$MODE" = check ]; then
    printf '%s  (ns %s, %s)\n' "$dep" "$ns" "$img"
    printf '  GHCR latest: %s\n' "${gd:-UNRESOLVED}"
    printf '  running:     %s\n' "${running:-UNKNOWN}"
    if [ -z "$gd" ]; then
      printf '  verdict: ERROR — could not resolve GHCR digest\n\n'
      rc=1
    elif [ -z "$running" ]; then
      printf '  verdict: WARN — no running pod digest (deployment down?)\n\n'
    elif [ "$gd" = "$running" ]; then
      printf '  verdict: MATCH (up to date)\n\n'
    else
      printf '  verdict: OUTDATED (would restart)\n\n'
    fi
    continue
  fi

  # watch mode — silent unless there is an update
  if [ -z "$gd" ]; then
    log "WARN ${dep} (${ns}): GHCR digest lookup failed (image ${img})"
    continue
  fi
  [ -z "$running" ] && continue   # deployment scaled to 0 / no pods — skip
  if [ "$gd" != "$running" ]; then
    log "UPDATE ${dep} (${ns}): ghcr ${gd} != running ${running} — rollout restart deploy/${dep}"
    "$KUBECTL" -n "$ns" rollout restart "deploy/${dep}" >> "$LOG" 2>&1 || \
      log "ERROR ${dep} (${ns}): rollout restart failed"
  fi
done
exit "$rc"
