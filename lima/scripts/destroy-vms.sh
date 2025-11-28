#!/bin/bash
set -euo pipefail

echo "Destroying K3s cluster VMs..."

# If two numeric arguments are provided, use the old behaviour (counts).
if [ "$#" -ge 2 ] && [[ "$1" =~ ^[0-9]+$ ]] && [[ "$2" =~ ^[0-9]+$ ]]; then
    CONTROL_PLANE_COUNT=$1
    WORKER_COUNT=$2

    # Stop and delete control plane nodes by count
    for i in $(seq 1 $CONTROL_PLANE_COUNT); do
        VM_NAME="k3s-control-$i"
        echo "Deleting $VM_NAME..."
        limactl stop "$VM_NAME" 2>/dev/null || true
        limactl delete "$VM_NAME" 2>/dev/null || true
    done

    # Stop and delete worker nodes by count
    for i in $(seq 1 $WORKER_COUNT); do
        VM_NAME="k3s-worker-$i"
        echo "Deleting $VM_NAME..."
        limactl stop "$VM_NAME" 2>/dev/null || true
        limactl delete "$VM_NAME" 2>/dev/null || true
    done
else
    # Auto-detect VMs whose names start with k3s-control- or k3s-worker-
    echo "No counts provided — auto-detecting VMs to delete..."

    # Get list of VM names from limactl. The output format may vary; handle missing matches gracefully.
    VM_NAMES=$(limactl list 2>/dev/null | awk 'NR>1 {print $1}' | grep -E '^k3s-(control|worker)-' || true)

    if [ -z "$VM_NAMES" ]; then
        echo "No k3s VMs found. Nothing to do."
    else
        for VM in $VM_NAMES; do
            echo "Deleting $VM..."
            limactl stop "$VM" 2>/dev/null || true
            limactl delete "$VM" 2>/dev/null || true
        done
    fi
fi

echo "Operation complete. Current VM list:"
limactl list || true
