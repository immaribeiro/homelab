#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TEMPLATE_DIR="$SCRIPT_DIR/../templates"

# Configuration
CONTROL_PLANE_COUNT=${1:-1}
WORKER_COUNT=${2:-2}

echo "Creating K3s cluster with Lima..."
echo "Control planes: $CONTROL_PLANE_COUNT"
echo "Workers: $WORKER_COUNT"

# Create control plane nodes
for i in $(seq 1 $CONTROL_PLANE_COUNT); do
    VM_NAME="k3s-control-$i"
    echo "Creating $VM_NAME..."
    
    # Copy template and customize
    cp "$TEMPLATE_DIR/control-plane.yaml" "/tmp/$VM_NAME.yaml"
    
    # Update hostname in template
    sed -i '' "s/k3s-control-1/$VM_NAME/g" "/tmp/$VM_NAME.yaml"
    
    # Update MAC address (increment last octet)
    MAC_SUFFIX=$(printf "%02d" $i)
    sed -i '' "s/52:55:55:00:00:01/52:55:55:00:00:$MAC_SUFFIX/g" "/tmp/$VM_NAME.yaml"
    
    # Create VM (non-interactive)
    limactl start -y --name="$VM_NAME" "/tmp/$VM_NAME.yaml"
    
    echo "$VM_NAME created successfully"
done

# Create worker nodes
for i in $(seq 1 $WORKER_COUNT); do
    VM_NAME="k3s-worker-$i"
    echo "Creating $VM_NAME..."
    
    # Copy template and customize
    cp "$TEMPLATE_DIR/worker.yaml" "/tmp/$VM_NAME.yaml"
    
    # Update hostname
    sed -i '' "s/k3s-worker-1/$VM_NAME/g" "/tmp/$VM_NAME.yaml"
    
    # Update MAC address (start from 10 to avoid conflicts)
    MAC_SUFFIX=$(printf "%02d" $((10 + i)))
    sed -i '' "s/52:55:55:00:00:02/52:55:55:00:00:$MAC_SUFFIX/g" "/tmp/$VM_NAME.yaml"
    
    # Update static IP address (192.168.5.11, 192.168.5.12, etc.)
    WORKER_IP="192.168.5.$((10 + i))"
    sed -i '' "s/192.168.5.11/$WORKER_IP/g" "/tmp/$VM_NAME.yaml"
    
    # Create VM (non-interactive)
    limactl start -y --name="$VM_NAME" "/tmp/$VM_NAME.yaml"
    
    echo "$VM_NAME created successfully"
done

echo ""
echo "All VMs created! Waiting for network initialization..."
sleep 10

echo ""
echo "VM List:"
limactl list

echo ""
echo "Getting VM IPs..."
for i in $(seq 1 $CONTROL_PLANE_COUNT); do
    VM_NAME="k3s-control-$i"
    IP=$(limactl shell "$VM_NAME" ip -4 addr show lima0 | grep inet | awk '{print $2}' | cut -d'/' -f1)
    echo "$VM_NAME: $IP"
done

for i in $(seq 1 $WORKER_COUNT); do
    VM_NAME="k3s-worker-$i"
    IP=$(limactl shell "$VM_NAME" ip -4 addr show lima0 | grep inet | awk '{print $2}' | cut -d'/' -f1)
    echo "$VM_NAME: $IP"
done

echo ""
echo "✅ VMs created successfully!"
echo ""
echo "Next steps (use Make commands for automation):"
echo "  1. make bootstrap       # Install SSH keys + passwordless sudo (~1 min)"
echo "  2. make inventory       # Generate Ansible inventory (instant)"
echo "  3. make install         # Install K3s cluster (~2-3 min)"
echo "  4. make kubeconfig      # Fetch kubeconfig (instant)"
echo "  5. make addons          # Install MetalLB, cert-manager, etc. (~2-3 min)"
echo "  6. make tunnel-setup    # Configure Cloudflare Tunnel (interactive first time)"
echo "  7. make status          # Verify cluster health"
echo ""
echo "Or run the full sequence: make cluster-setup"
echo "Then configure tunnel: make tunnel-setup && kubectl apply -f k8s/cloudflared/tunnel.yaml"
