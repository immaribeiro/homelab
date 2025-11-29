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
    
    # Create VM
    limactl start --name="$VM_NAME" "/tmp/$VM_NAME.yaml"
    
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
    
    # Create VM
    limactl start --name="$VM_NAME" "/tmp/$VM_NAME.yaml"
    
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
echo "Next steps:"
echo "1. Generate Ansible inventory: cd ../terraform && terraform apply"
echo "2. Install K3s: cd ../ansible && ansible-playbook -i inventory.yml playbooks/k3s-install.yml"
