# K3s Home Lab - Detailed Setup Guide

This guide walks you through setting up a complete K3s cluster on macOS using Lima, Terraform, and Ansible.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Automated Setup](#automated-setup)
3. [Manual Setup](#manual-setup)
4. [Creating VMs](#creating-vms)
5. [Installing K3s](#installing-k3s)
6. [Accessing Your Cluster](#accessing-your-cluster)
7. [Verification](#verification)

## Prerequisites

- **macOS** (M1/M2/M3/M4 or Intel)
- **Homebrew** installed
- **Minimum 8GB RAM** available (16GB recommended)
- **Minimum 30GB free disk space**

## Automated Setup

The easiest way to set up all prerequisites is to use the included `setup.sh` script:

```bash
# Clone or navigate to your homelab directory
cd ~/GitHub/homelab

# Run the setup script
bash setup.sh
```

This script will:
- ✓ Check for Homebrew
- ✓ Install lima, terraform, ansible, socket_vmnet
- ✓ Start socket_vmnet service
- ✓ Copy socket_vmnet binary to expected location
- ✓ Configure Lima sudoers
- ✓ Make scripts executable

## Manual Setup

If you prefer to set up manually, follow these steps:

### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Required Tools

```bash
brew install lima terraform ansible socket_vmnet
```

### 3. Start socket_vmnet Service

```bash
sudo brew services start socket_vmnet

# Verify it's running
sudo brew services list | grep socket_vmnet
```

### 4. Copy socket_vmnet Binary

Lima looks for socket_vmnet at `/opt/socket_vmnet/bin/socket_vmnet`, but Homebrew installs it elsewhere. We need to copy it:

```bash
# Find socket_vmnet version
SOCKET_VERSION=$(ls /opt/homebrew/Cellar/socket_vmnet/ | head -1)

# Create destination directory and copy
sudo mkdir -p /opt/socket_vmnet/bin
sudo cp /opt/homebrew/Cellar/socket_vmnet/$SOCKET_VERSION/bin/socket_vmnet /opt/socket_vmnet/bin/socket_vmnet

# Verify
ls -la /opt/socket_vmnet/bin/socket_vmnet
```

### 5. Configure Lima Sudoers

Lima needs sudo privileges to manage VMs:

```bash
limactl sudoers > /tmp/etc_sudoers.d_lima
sudo install -o root /tmp/etc_sudoers.d_lima "/private/etc/sudoers.d/lima"
rm /tmp/etc_sudoers.d_lima

# Verify
cat /private/etc/sudoers.d/lima
```

### 6. Make Scripts Executable

```bash
chmod +x lima/scripts/create-vms.sh
chmod +x lima/scripts/destroy-vms.sh
```

## Creating VMs

### Option 1: Using Terraform (Recommended)

```bash
cd terraform

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply configuration (this creates the VMs)
terraform apply

# View outputs
terraform output
```

### Option 2: Direct Script

```bash
# Create 1 control plane and 2 worker nodes
bash lima/scripts/create-vms.sh 1 2

# Or with different configuration
bash lima/scripts/create-vms.sh 3 5  # Creates 3 control planes and 5 workers
```

### Verify VMs are Created

```bash
limactl list

# Expected output:
# NAME             STATUS     SSH            VMTYPE    ARCH       CPUS    MEMORY    DISK
# k3s-control-1    Running    127.0.0.1:...  vz        aarch64    2       4GiB      20GiB
# k3s-worker-1     Running    127.0.0.1:...  vz        aarch64    2       3GiB      15GiB
# k3s-worker-2     Running    127.0.0.1:...  vz        aarch64    2       3GiB      15GiB
```

### Check VM IPs

```bash
# Get control plane IP
limactl shell k3s-control-1 ip -4 addr show lima0 | grep inet

# Get worker IPs
limactl shell k3s-worker-1 ip -4 addr show lima0 | grep inet
limactl shell k3s-worker-2 ip -4 addr show lima0 | grep inet
```

## Installing K3s

### Generate Ansible Inventory

If you used Terraform, the inventory is automatically generated. If not:

```bash
# Manually create inventory based on VM IPs
# Edit ansible/inventory.yml with your VM IPs
```

### Install K3s Cluster

```bash
cd ansible

# Run the K3s installation playbook
ansible-playbook -i inventory.yml playbooks/k3s-install.yml

# This will:
# 1. Prepare all nodes (install prerequisites)
# 2. Install K3s control plane
# 3. Install K3s on worker nodes
# 4. Wait for all nodes to be ready
# 5. Display cluster status
```

### Watch the Installation

```bash
# In another terminal, watch K3s logs
limactl shell k3s-control-1 sudo journalctl -u k3s -f
```

## Accessing Your Cluster

### Get kubeconfig

```bash
# Get the control plane IP
CONTROL_IP=$(limactl shell k3s-control-1 ip -4 addr show lima0 | grep inet | awk '{print $2}' | cut -d'/' -f1)

# Copy kubeconfig from control plane
limactl shell k3s-control-1 sudo cat /etc/rancher/k3s/k3s.yaml > ~/.kube/config

# Update kubeconfig with correct IP (replace 127.0.0.1 with actual control plane IP)
sed -i '' "s/127.0.0.1/$CONTROL_IP/g" ~/.kube/config

# Verify permissions
chmod 600 ~/.kube/config
```

### Test Connectivity

```bash
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A
```

## Verification

### Check Cluster Health

```bash
# Nodes should all be Ready
kubectl get nodes
# Expected: All nodes with STATUS "Ready"

# All control plane components should be Running
kubectl get pods -n kube-system
# Expected: All pods with STATUS "Running" or "Completed"

# Check CNI (Flannel)
kubectl get pods -n kube-flannel
# Expected: Flannel pods running on each node

# Check CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns
# Expected: CoreDNS pods running
```

### Deploy Test Application

```bash
# Deploy a simple nginx to test the cluster
kubectl create deployment nginx --image=nginx:latest

# Verify deployment
kubectl get deployment
kubectl get pods

# Scale up
kubectl scale deployment nginx --replicas=3

# Check pods are distributed across nodes
kubectl get pods -o wide

# Clean up
kubectl delete deployment nginx
```

### Test Inter-node Connectivity

```bash
# SSH into control plane
limactl shell k3s-control-1

# From inside VM, test connectivity to workers
ping -c 3 <worker-1-ip>
ping -c 3 <worker-2-ip>
```

## Common Operations

### SSH into a VM

```bash
limactl shell k3s-control-1
limactl shell k3s-worker-1
```

### Stop/Start VMs

```bash
# Stop all VMs
limactl stop k3s-control-1 k3s-worker-1 k3s-worker-2

# Start all VMs
limactl start k3s-control-1 k3s-worker-1 k3s-worker-2

# Restart a VM
limactl stop k3s-control-1 && limactl start k3s-control-1
```

### Reset K3s (Keep VMs)

```bash
cd ansible

# Uninstall K3s from all nodes
ansible-playbook -i inventory.yml playbooks/k3s-reset.yml

# Reinstall K3s
ansible-playbook -i inventory.yml playbooks/k3s-install.yml
```

### Destroy Everything

```bash
# Destroy using Terraform
cd terraform
terraform destroy

# Or manually delete VMs
bash lima/scripts/destroy-vms.sh 1 2

# Clean up local files
rm -rf ~/.lima/k3s-*
```

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed troubleshooting steps.

Common issues:
- socket_vmnet not running → see socket_vmnet section
- VMs not communicating → check network configuration
- K3s nodes not joining → check Ansible logs
- kubeconfig access issues → check IP in kubeconfig
