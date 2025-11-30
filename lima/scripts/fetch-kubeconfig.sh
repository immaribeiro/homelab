#!/usr/bin/env bash
set -euo pipefail

# Fetch K3s kubeconfig from control-plane VM and rewrite server to lima0 IP
# Usage: ./lima/scripts/fetch-kubeconfig.sh [control_vm_name] [control_ip]
# Defaults: control_vm_name=k3s-control-1, control_ip=192.168.105.2

VM_NAME=${1:-k3s-control-1}
CONTROL_IP=${2:-192.168.105.2}
DEST=${KUBECONFIG:-$HOME/.kube/config}

mkdir -p "$(dirname "$DEST")"

echo "Fetching kubeconfig from ${VM_NAME} to ${DEST}..."
limactl cp "${VM_NAME}:/etc/rancher/k3s/k3s.yaml" "$DEST.tmp"

echo "Patching server to https://${CONTROL_IP}:6443..."
sed -E "s#https://127.0.0.1:6443#https://${CONTROL_IP}:6443#g" "$DEST.tmp" > "$DEST"
rm -f "$DEST.tmp"

echo "Setting current context to use ${DEST}..."
export KUBECONFIG="$DEST"

echo "Verifying cluster connectivity..."
kubectl cluster-info
kubectl get nodes -o wide

echo "OK: kubeconfig ready at $DEST"
