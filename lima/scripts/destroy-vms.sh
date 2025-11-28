#!/bin/bash
set -e

CONTROL_PLANE_COUNT=${1:-1}
WORKER_COUNT=${2:-2}

echo "Destroying K3s cluster VMs..."

# Stop and delete control plane nodes
for i in $(seq 1 $CONTROL_PLANE_COUNT); do
    VM_NAME="k3s-control-$i"
    echo "Deleting $VM_NAME..."
    limactl stop "$VM_NAME" 2>/dev/null || true
    limactl delete "$VM_NAME" 2>/dev/null || true
done

# Stop and delete worker nodes
for i in $(seq 1 $WORKER_COUNT); do
    VM_NAME="k3s-worker-$i"
    echo "Deleting $VM_NAME..."
    limactl stop "$VM_NAME" 2>/dev/null || true
    limactl delete "$VM_NAME" 2>/dev/null || true
done

echo "All VMs destroyed!"
limactl list
