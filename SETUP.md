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
8. [Add-ons & Ingress](#add-ons--ingress)
9. [TLS & Certificates](#tls--certificates)
10. [Cloudflare Tunnel & DNS](#cloudflare-tunnel--dns)
11. [Monitoring & Dashboards](#monitoring--dashboards)
12. [Homepage Dashboard](#homepage-dashboard)
13. [Post-Install Validation](#post-install-validation)
14. [Backup & Maintenance](#backup--maintenance)
15. [Next Steps](#next-steps)

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
chmod +x lima/scripts/*.sh scripts/*.sh
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

### Bootstrap SSH access on VMs

Before running Ansible, install your SSH public key and enable passwordless sudo on each VM:

```bash
# Uses ~/.ssh/id_ed25519.pub by default (set PUBKEY_PATH to override)
bash lima/scripts/bootstrap-ssh.sh k3s-control-1 k3s-worker-1 k3s-worker-2
```

### Check VM IPs

```bash
# Get control plane IP
limactl shell k3s-control-1 ip -4 addr show lima0 | grep inet

# Get worker IPs
limactl shell k3s-worker-1 ip -4 addr show lima0 | grep inet
limactl shell k3s-worker-2 ip -4 addr show lima0 | grep inet
```

## Networking

- Ansible SSH: Uses `127.0.0.1:<port>` forwarded by Lima per VM. See `ansible/inventory-static-ip.yml` for `ansible_host` and `ansible_port`.
- Cluster IPs: K3s uses `lima0` network (`192.168.105.x`) for node-to-node communication. These IPs are routable between VMs and stable per MAC.
- Lima `shared`/socket_vmnet: Does not bridge `eth0` VM-to-VM on `192.168.5.0/24` (ARP fails). Do not use `eth0` for K3s networking.
- K3s flags: Server/agents run with `--flannel-iface lima0`, `--node-ip` and `--node-external-ip` set to the `lima0` IP. Agents set `K3S_AGENT_BOOTSTRICT_MODE=false` to bypass localhost-only supervisor bootstrap.

Quick sanity check:

```bash
bash lima/scripts/cluster-status.sh
```

## Installing K3s

### Generate Ansible Inventory

If you used Terraform, the inventory is automatically generated. If not:

```bash
# Generate inventory from current Lima state (forwarded SSH + lima0 IPs)
bash lima/scripts/generate-inventory-from-limactl.sh > ansible/inventory-static-ip.yml
```

### Install K3s Cluster

```bash
cd ansible

# Run the K3s installation playbook
ansible-playbook -i inventory-static-ip.yml playbooks/k3s-install.yml

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

## Add-ons & Ingress

Install networking, certificates, and optional dashboard/monitoring components via Make targets:

```bash
make addons          # MetalLB + cert-manager + issuers + wildcard cert
make ingress-nginx   # Ingress controller (LoadBalancer)
make tunnel-setup    # Create/reuse Cloudflare Tunnel and update .env
make tunnel          # Apply cloudflared deployment + config (after env set)
make deploy-home     # Homepage dashboard deployment
make metrics         # Prometheus / Grafana / Alertmanager stack
```

Applied resources:
- MetalLB controller + address pool (`k8s/metallb/metallb-config.yaml`)
- cert-manager controllers (v1.15.3) + ClusterIssuers + wildcard certificate for `*.immas.org`
- Cloudflare API token secret (`cloudflare-api-token-secret`)
- NGINX ingress controller (namespace `ingress-nginx`)
- Cloudflare Tunnel deployment + routing ConfigMap (`k8s/cloudflared/tunnel.yaml`)
- Homepage dashboard (`k8s/manifests/home.yml`)
- Monitoring stack (Helm: kube-prometheus-stack) with custom values (`k8s/monitoring/values.yaml`)

Readiness checks:
```bash
kubectl -n metallb-system get pods
kubectl -n cert-manager get pods
kubectl -n ingress-nginx get svc ingress-nginx-controller
kubectl -n cloudflared get deploy,po
kubectl -n monitoring get pods
```

## TLS & Certificates

Certificate lifecycle:
1. Secret with Cloudflare API token (`make cf-secret`).
2. ClusterIssuer (prod & staging) performs DNS-01 for wildcard.
3. ACME Order + Challenge succeed; secret `wildcard-immas-org-tls` created (referenced by Ingress or Tunnel routes where TLS termination occurs).

Checks:
```bash
kubectl describe certificate wildcard-immas-org-tls
kubectl get secret wildcard-immas-org-tls
```

If pending:
```bash
kubectl -n cert-manager logs deploy/cert-manager | grep -i cloudflare
```

## Cloudflare Tunnel & DNS

Prerequisites: created tunnel ID + credentials JSON via `cloudflared tunnel create` locally.

Deploy tunnel:
```bash
export TUNNEL_ID=<id>
export TUNNEL_CRED_FILE=~/path/to/<id>.json
make tunnel
```

Add wildcard DNS (Cloudflare dashboard): CNAME `*.immas.org` -> `<TUNNEL_ID>.cfargotunnel.com`.

Verify:
```bash
dig +short hello.lab.immas.org
curl -I https://hello.lab.immas.org
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

## Reset & Reinstall (From Scratch)

Use these steps to completely remove and reinstall the cluster.

### One-shot Teardown

```bash
# From repo root
bash lima/scripts/teardown.sh
```

Flags (environment variables):
- `UNINSTALL_K3S=0` to skip K3s uninstall via Ansible.
- `CLEAN_KUBECONFIG=0` to keep `~/.kube/config`.
- `DEEP_CLEAN=1` to also remove `~/.lima/k3s-*`.

### Fresh Install

```bash
# 1) Ensure prerequisites
bash setup.sh

# 2) Create VMs
bash lima/scripts/create-vms.sh 1 2

# 3) Generate inventory from current limactl state
bash lima/scripts/generate-inventory-from-limactl.sh > ansible/inventory-static-ip.yml

# 4) Install K3s using forwarded SSH and lima0 node_ip
cd ansible
ansible-playbook -i inventory-static-ip.yml playbooks/k3s-install.yml

# 5) Verify
cd ..
bash lima/scripts/cluster-status.sh
```

## Monitoring & Dashboards

Install the metrics stack (Prometheus, Alertmanager, Grafana) after base add-ons:
```bash
make metrics
```
Grafana admin credentials are stored in the `grafana-admin` secret (override with `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` in `.env` before running `make metrics`).

Access:
- Grafana: `https://grafana.immas.org`
- Prometheus (internal): `http://monitoring-prometheus.monitoring.svc.cluster.local:9090`
- Alertmanager (internal): `http://monitoring-alertmanager.monitoring.svc.cluster.local:9093`

Basic validation:
```bash
kubectl -n monitoring get pods
kubectl -n monitoring get prometheusrules
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090 &
open http://localhost:9090/targets
```

## Homepage Dashboard

Deploy central dashboard aggregating links and widgets:
```bash
make deploy-home
```
Key notes:
- Writable config achieved via `emptyDir` + initContainer (see `k8s/manifests/home.yml`).
- Set `HOMEPAGE_ALLOWED_HOSTS=home.immas.org` in Deployment env for host validation.
- Update services/widgets/settings in the ConfigMap then restart: `kubectl rollout restart deployment/homepage -n homepage`.

## Deploying Applications

### Environment Variables
Copy `.env.example` to `.env` and fill in your actual values:
```bash
cp .env.example .env
# Edit .env with your credentials
```

**Important:** Never commit `.env` to version control!

### Deploy Home Assistant
```bash
# Apply manifest
kubectl apply -f k8s/manifests/home-assistant.yml

# Wait for pod to be ready
kubectl -n home-assistant get pods -w

# Configure trusted proxies (after first start)
kubectl -n home-assistant exec deploy/home-assistant -- sh -c 'cat > /config/configuration.yaml << EOF
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 10.42.0.0/16
    - 10.43.0.0/16
EOF'

# Restart to apply config
kubectl -n home-assistant rollout restart deployment/home-assistant

# Add to Cloudflare Tunnel dashboard:
# - Subdomain: ha
# - Domain: immas.org
# - Service: http://192.168.105.51:80

# Test access
curl -I https://ha.immas.org
```

### Deploy Additional Apps
Follow the pattern in `k8s/README.md`:
1. Create Deployment + Service (Ingress optional if using tunnel direct service route)
2. Add hostname route in `k8s/cloudflared/tunnel.yaml` ConfigMap
3. Apply manifest: `kubectl apply -f k8s/manifests/<app>.yml`
4. Test external access: `curl -I https://<subdomain>.immas.org`

## Post-Install Validation

Run these checks after initial setup + add-ons:
```bash
kubectl get nodes -o wide
kubectl get pods -A | grep -v Running | grep -v Completed || echo "All pods healthy"
kubectl get svc -A | grep LoadBalancer || true
kubectl -n cert-manager get certificate
kubectl -n cloudflared logs deploy/cloudflared --tail=30 | grep -i connected || echo "Tunnel logs OK"
kubectl -n monitoring get pods | grep grafana && echo "Monitoring stack present"
curl -I https://home.immas.org
```

## Backup & Maintenance

Use the built-in backup target to snapshot key app configs (Home Assistant, Plex):
```bash
make backup
```
Outputs are placed under `backups/<timestamp>/`. Tarballs contain application configuration for offline storage.

Regular tasks:
- Rotate API tokens & credentials in `.env`.
- Update Helm chart versions (`make metrics` after `helm repo update`).
- Review Cloudflare Tunnel routes for unused hosts.

## Next Steps

Enhance the platform:
- Add dynamic storage (Longhorn) for PVC provisioning.
- Introduce GitOps (ArgoCD or Flux) for declarative app lifecycle.
- Add secret management (Sealed Secrets / External Secrets Operator).
- Harden access with Cloudflare Zero Trust policies.
- Extend alerting & recording rules for SLO-based monitoring.
- Enrich Homepage with authenticated widgets (Prometheus/Grafana/Home Assistant APIs).

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed troubleshooting steps.

Common issues:
- socket_vmnet not running → see socket_vmnet section
- VMs not communicating → check network configuration
- K3s nodes not joining → check Ansible logs
- kubeconfig access issues → check IP in kubeconfig
