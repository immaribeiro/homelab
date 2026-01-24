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

### 6b. Install NGINX Ingress Controller (CRITICAL)
```bash
make ingress-nginx
```
Installs NGINX Ingress Controller v1.11.1 with LoadBalancer service. This is **required** for your manifests to work.
Verify it's running and has an external IP assigned:
```bash
kubectl -n ingress-nginx get svc ingress-nginx-controller
# Should show EXTERNAL-IP like 192.168.105.50
```
**Note:** K3s includes Traefik by default, but your application manifests are configured for NGINX. Without this step, ingresses will not be routable.

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

# Deploy qBittorrent
kubectl apply -f k8s/manifests/qbittorrent.yml

# Deploy Homepage dashboard
make deploy-home

# (Optional) Install monitoring stack (Prometheus, Grafana, Alertmanager)
make metrics

# Deploy Vaultwarden (Bitwarden-compatible)
make deploy-vault

# Deploy FileBrowser (file server)
make deploy-files
make tunnel-route HOST=files.immas.org

# Deploy LM Studio (LLM chat interface)
make deploy-chat
make tunnel-route HOST=llm.immas.org

# Deploy Homelab Telegram Bot (qB integration)
make deploy-bot BOT_TOKEN=... CHAT_ID=... QB_USER=... QB_PASS=... [QB_URL=...]
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

External (Cloudflare Tunnel):
- Homepage: `https://home.immas.org`
- Home Assistant: `https://ha.immas.org`
- Plex: `https://plex.immas.org`
- qBittorrent: `https://qb.immas.org`
- Grafana: `https://grafana.immas.org`
- Vaultwarden: `https://vault.immas.org`
- ArgoCD: `https://argocd.immas.org`
- LM Studio Chat: `https://llm.immas.org`
- FileBrowser: `https://files.immas.org`
- Grafana: `https://grafana.immas.org`
- Vaultwarden: `https://vault.immas.org`

Internal Cluster-only (default):
- Prometheus: `http://monitoring-prometheus.monitoring.svc.cluster.local:9090`
- Alertmanager: `http://monitoring-alertmanager.monitoring.svc.cluster.local:9093`

Local network (load balancer IP) access for ingress-nginx:
```bash
kubectl -n ingress-nginx get svc ingress-nginx-controller
# Use http://<EXTERNAL-IP> for direct cluster ingress testing
```

## qBittorrent: Add Magnet (CLI)

Use the provided Make target or script to submit magnet links to qBittorrent over HTTPS (with proper headers):

```bash
# Via Make (recommended)
make qb-add MAGNET='magnet:?xt=urn:btih:...'

# Optional: set a save path inside the container (maps to your Mac folder)
make qb-add MAGNET='magnet:?xt=urn:btih:...' SAVEPATH=/downloads

# Direct script usage
scripts/qb-add.sh 'magnet:?xt=urn:btih:...' --savepath /downloads
```

Notes:
- Defaults: `QB_HOST=https://qb.immas.org`, `QB_USER=admin`, `QB_PASS=adminadmin`.
- Override by exporting env vars or passing flags to the script.
- The script sends Referer/Origin headers to satisfy CSRF/WAF when using Cloudflare Tunnel.


## Cloudflare DNS Routing Automation

To avoid manual DNS edits in the Cloudflare dashboard, use the built-in Job and Make targets to create CNAMEs that route to your tunnel.

Prerequisite: run `cloudflared login` on your Mac once (creates `~/.cloudflared/cert.pem`). Set either `TUNNEL_NAME` or `TUNNEL_ID` in `.env`.

```bash
# Route vault.immas.org
make tunnel-route-vault-dns

# Route any hostname
make tunnel-route HOST=sub.immas.org

# Verify resolution + HTTPS
make verify-host HOST=sub.immas.org
```

Troubleshooting:
- If `curl` fails with DNS resolution on your Mac but works on other devices, a VPN resolver may be caching/overriding DNS. Flush cache or set Ethernet DNS to Cloudflare temporarily.
- HTTP 530 from Cloudflare edge usually means the public hostname isn’t fully associated to the tunnel yet; confirm in Zero Trust → Tunnels → Public Hostnames or re-run the route target.

## Vaultwarden Notes

After the first admin account is created, disable open signups:
```bash
kubectl -n vaultwarden set env deploy/vaultwarden SIGNUPS_ALLOWED=false
```

The Deployment sets:
- `DOMAIN=https://vault.immas.org`
- `WEBSOCKET_ENABLED=true`
- `WEB_VAULT_ENABLED=true`

## Homelab Telegram Bot

Deploy:
```bash
make deploy-bot BOT_TOKEN=... CHAT_ID=... QB_USER=... QB_PASS=... [QB_URL=...]
```

Commands:
- `/start`, `/help`, `/status`, `/version`, `/add <magnet>`, `/id`

Behavior:
- Only the whitelisted `CHAT_ID` can interact; magnets are submitted to qBittorrent.
- Configuration is passed via Secret/ConfigMap at deploy-time.

## FileBrowser (File Server)

Deploy:
```bash
make deploy-files
make tunnel-route HOST=files.immas.org
```

Access: `https://files.immas.org`

Default credentials:
- Username: `admin`
- Password: Check pod logs: `kubectl -n files logs -l app=filebrowser | grep password`
- **Change password immediately** after first login!

Features:
- Web-based file upload/download
- Drag & drop interface
- File preview (images, videos, PDFs)
- Create public share links
- User management
- 20GB storage (expandable)

Management:
```bash
make files-status    # Check status
make files-logs      # View logs
make files-restart   # Restart service
```

Expand storage:
```bash
kubectl -n files edit pvc filebrowser-data
# Change: storage: 20Gi → storage: 50Gi
```

Future NAS mounting:
When you add external drives, update the deployment to mount them as hostPath volumes and they'll appear in FileBrowser.

## Troubleshooting

### Cloudflare Tunnel 530 Errors
- Verify services exist: `kubectl get svc -A`
- Check tunnel logs: `kubectl -n cloudflared logs -l app=cloudflared`
- Ensure ingress routes match deployed services
 - Ensure the public hostname is attached to the Tunnel (Zero Trust → Tunnels → Public Hostnames)
 - If necessary, route using tunnel name instead of UUID: `cloudflared tunnel route dns <TUNNEL_NAME> <host>`

### Certificate Not Ready
```bash
kubectl -n cert-manager get certificate
kubectl -n cert-manager describe certificate wildcard-immas-org
```
Wait 2-5 minutes for DNS-01 challenge to complete.

### VMs Not Responding
### Homepage Dashboard Issues
- 500 error with EROFS writes: ConfigMap was mounted read-only; ensure initContainer copies files into `emptyDir` at `/app/config` (see `k8s/manifests/home.yml`).
- Host validation failed: Set env `HOMEPAGE_ALLOWED_HOSTS=home.immas.org` in Deployment.
- Services blank: `services.yaml` must be a top-level list of groups, not nested under a `services:` key.

### Monitoring Stack Issues
- Grafana login fails: Verify `grafana-admin` Secret (created by `make metrics`). Re-run target if missing.
- Prometheus targets down: Port-forward and inspect `/targets` to confirm ServiceMonitor selectors.
```bash
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
open http://localhost:9090/targets
```
- Alertmanager empty: Check loaded rules `kubectl -n monitoring get prometheusrules`; add alerting / recording rules via values overrides.

### Rotate Grafana Password (Helm-managed)

The default admin password is `admin`. To rotate it via Helm (recommended for GitOps):

```bash
# Set a new password via Helm upgrade
make grafana-set-password PASSWORD='YourNewPassword'

# Or manually edit k8s/monitoring/values.yaml:
# grafana:
#   adminPassword: YourNewPassword
# Then redeploy:
make metrics
```

For immediate runtime password changes without Helm:
```bash
# Reset password in the DB (takes effect immediately)
make grafana-reset PASSWORD='YourNewPassword'

# Then sync the Kubernetes secret to match (ensures persistence across restarts)
make grafana-secret-sync PASSWORD='YourNewPassword'
```

See `TROUBLESHOOTING.md` → [Grafana Password & Login](#grafana-password--login) for password source precedence and detailed diagnosis steps.
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
