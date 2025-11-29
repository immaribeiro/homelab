#!/bin/zsh
set -euo pipefail

CONTROL_VM=${1:-k3s-control-1}

echo "[Cluster Nodes]"
limactl shell "$CONTROL_VM" kubectl get nodes -o wide || {
  echo "kubectl not ready on $CONTROL_VM" >&2
  exit 1
}

echo "\n[All Pods]"
limactl shell "$CONTROL_VM" kubectl get pods -A -o wide || {
  echo "kubectl not ready on $CONTROL_VM" >&2
  exit 1
}
