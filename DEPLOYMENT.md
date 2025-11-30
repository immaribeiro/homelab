# Homelab Deployment Guide

Complete guide for deploying the K3s homelab from scratch with Cloudflare Tunnel integration.

## Prerequisites

- macOS with Lima installed (`brew install lima`)
- Ansible installed (`brew install ansible`)
- kubectl installed (`brew install kubectl`)
- cloudflared CLI installed (`brew install cloudflared`)
- Cloudflare account with active zone

## Full Deployment Sequence

### 1. Create VMs
```bash
make create
```
Creates 3 Lima VMs (1 control plane, 2 workers) with writable home directory mounts.

### 2. Bootstrap SSH Access
```bash
make bootstrap
```
Installs SSH keys and configures passwordless sudo on all VMs (~1 min).

### 3. Generate Ansible Inventory
```bash
make inventory
```
Generates `ansible/inventory.yml` from current Lima VM SSH ports and static IPs (instant).

### 4. Install K3s
```bash
make install
```
Deploys K3s via Ansible playbooks (~2-3 min).

### 5. Fetch Kubeconfig
```bash
make kubeconfig
```
Retrieves kubeconfig from control plane and patches server IP (instant).

### 6. Install Add-ons
```bash
make addons
```
Installs MetalLB, cert-manager, Cloudflare API secret, ClusterIssuers, and wildcard certificate (~2-3 min).

### 7. Configure Cloudflare Tunnel
```bash
make tunnel-setup
```
- Authenticates with Cloudflare (browser prompt on first run)
- Reuses or creates tunnel named `homelab`
- Updates `.env` with `CLOUDFLARE_TUNNEL_ID` and `CLOUDFLARE_TUNNEL_CRED_FILE`
- Creates Kubernetes secret `cloudflared-credentials`

Then update `k8s/cloudflared/tunnel.yaml` with the tunnel UUID and apply:
```bash
# Update the tunnel: field in k8s/cloudflared/tunnel.yaml to match CLOUDFLARE_TUNNEL_ID
kubectl apply -f k8s/cloudflared/tunnel.yaml
```

### 8. Deploy Applications
```bash
# Deploy Plex
kubectl apply -f k8s/manifests/plex.yml

# Deploy Home Assistant (if not already deployed)
kubectl apply -f k8s/manifests/home-assistant.yml
```

### 9. Verify Deployment
```bash
make status
kubectl -n cloudflared logs -l app=cloudflare -f
kubectl get pods -A
```

## Environment Variables

The `.env` file contains all configuration. Required variables:

```bash
# Cloudflare
CLOUDFLARE_ZONE_API_TOKEN=<your-api-token>
CLOUDFLARE_TUNNEL_ID=<tunnel-uuid>
CLOUDFLARE_TUNNEL_NAME=homelab
CLOUDFLARE_TUNNEL_CRED_FILE=/Users/<you>/.cloudflared/<tunnel-uuid>.json

# K3s
K3S_CONTROL_PLANE_IP=192.168.5.10

# MetalLB
METALLB_IP_RANGE=192.168.5.50-192.168.5.60

# Plex (optional)
PLEX_CLAIM_TOKEN=<your-plex-claim-token>
```

## Automated Setup (All-in-One)

For a complete deployment from scratch:
```bash
make create
make cluster-setup  # Runs: bootstrap → inventory → install
make kubeconfig
make addons
make tunnel-setup
# Edit k8s/cloudflared/tunnel.yaml with CLOUDFLARE_TUNNEL_ID
kubectl apply -f k8s/cloudflared/tunnel.yaml
```

## Reset/Teardown

```bash
# Full teardown (uninstall K3s, remove VMs, clean kubeconfig)
UNINSTALL_K3S=true CLEAN_KUBECONFIG=true DEEP_CLEAN=true make teardown

# Remove generated inventory
make clean
```

## Accessing Services

- **Via Cloudflare Tunnel (external):**
  - Home Assistant: `https://ha.immas.org`
  - Plex: `https://plex.immas.org`
  - Home: `https://home.immas.org`

- **Via Local Network:**
  - Get MetalLB IP: `kubectl -n ingress-nginx get svc`
  - Access via `http://<metallb-ip>`

## Troubleshooting

### Cloudflare Tunnel 530 Errors
- Verify services exist: `kubectl get svc -A`
- Check tunnel logs: `kubectl -n cloudflared logs -l app=cloudflared`
- Ensure ingress routes match deployed services

### Certificate Not Ready
```bash
kubectl -n cert-manager get certificate
kubectl -n cert-manager describe certificate wildcard-immas-org
```
Wait 2-5 minutes for DNS-01 challenge to complete.

### VMs Not Responding
```bash
limactl list
limactl shell <vm-name>
# Check network: ip addr show eth0
```

### SSH Issues
```bash
# Re-run bootstrap
make bootstrap
# Test manually
ssh -p <port> ubuntu@127.0.0.1
```

## File Structure

```
homelab/
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Template
├── Makefile                      # Automation targets
├── ansible/
│   ├── inventory.yml             # Generated from Lima VMs
│   └── playbooks/                # K3s installation playbooks
├── k8s/
│   ├── cloudflared/
│   │   └── tunnel.yaml           # Tunnel config + deployment
│   ├── cert-manager/             # Certificates & issuers
│   ├── metallb/                  # LoadBalancer config
│   └── manifests/                # App deployments
├── lima/
│   ├── scripts/                  # VM management scripts
│   └── templates/                # Lima VM definitions
└── scripts/
    └── cloudflared-setup.sh      # Tunnel automation
```
