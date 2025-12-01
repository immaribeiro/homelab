# Environment Variables Guide

This project uses a `.env` file to manage configuration and secrets.

## Setup

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Fill in your actual values** in `.env` (never commit this file!)

3. **The Makefile automatically loads `.env`** when you run make targets

## Variable Usage

### Directly Used by Makefile

These variables are read by the Makefile and used in commands:

| Variable | Usage | Required For |
|----------|-------|--------------|
| `CLOUDFLARE_ZONE_API_TOKEN` | Create Kubernetes secret for cert-manager | `make cf-secret` |
| `K3S_CONTROL_PLANE_IP` | Fetch kubeconfig from control plane | `make kubeconfig` |
| `TUNNEL_ID` | Cloudflare Tunnel UUID for deployment | `make tunnel` / `make tunnel-setup` |
| `TUNNEL_CRED_FILE` | Path to tunnel credentials JSON | `make tunnel` / `make tunnel-setup` |
| `TUNNEL_NAME` | Cloudflare Tunnel name (alternative to UUID) | `make tunnel-route*` |

### Documentation Only (Hardcoded in YAML)

These variables document the values used in static YAML files. To change them, you must manually edit the corresponding files:

| Variable | File(s) | Description |
|----------|---------|-------------|
| `METALLB_IP_RANGE` | `k8s/metallb/metallb-config.yaml` | IP pool for LoadBalancer services |
| `NGINX_INGRESS_IP` | Assigned by MetalLB | LoadBalancer IP for NGINX Ingress |
| `K8S_POD_NETWORK` | K3s default | Pod CIDR (hardcoded in K3s) |
| `K8S_SERVICE_NETWORK` | K3s default | Service CIDR (hardcoded in K3s) |
| `CLOUDFLARE_TUNNEL_TOKEN` | `kubectl create secret` | Token for Cloudflare Tunnel auth |
| `HOME_ASSISTANT_STORAGE_SIZE` | `k8s/manifests/home-assistant.yml` | PVC size for Home Assistant |
| `HOME_ASSISTANT_TIMEZONE` | `k8s/manifests/home-assistant.yml` | Timezone env var |
| `HOMEPAGE_ALLOWED_HOSTS` | `k8s/manifests/home.yml` | Allowed host(s) for Homepage domain validation |
| `HOMEPAGE_VAR_TITLE` | `k8s/manifests/home.yml` | Dashboard title override |

### Telegram Bot (Deploy-time Secrets)

These are passed via `make deploy-bot` and stored as a Kubernetes Secret/ConfigMap at deploy time.

| Variable | Purpose | Default |
|----------|---------|---------|
| `BOT_TOKEN` | Telegram Bot API token | – |
| `CHAT_ID` | Allowed chat ID (whitelist) | – |
| `QB_USER` | qBittorrent username | – |
| `QB_PASS` | qBittorrent password | – |
| `QB_URL` | qBittorrent base URL | `http://qbittorrent.qbittorrent.svc.cluster.local:8080` |
| `SAVE_PATH` | Default save path for torrents | `/downloads` |
| `AUTO_TMM` | Enable qB automatic torrent management | `false` |

### Reference Only

These are for your reference and future automation:

| Variable | Purpose |
|----------|---------|
| `CLOUDFLARE_ACCOUNT_ID` | Your Cloudflare account ID |
| `CLOUDFLARE_ZONE_ID` | DNS zone ID for your domain |
| `CLOUDFLARE_TUNNEL_ID` | Tunnel UUID from Cloudflare dashboard |
| `BASE_DOMAIN` | Your main domain name |
| `GITHUB_REPO` | This repository (for GitOps) |

## Security

- **Never commit `.env`** - it's in `.gitignore`
- `.env.example` should only contain placeholder values
- Rotate tokens regularly
- Use dedicated API tokens with minimal permissions

## Updating Values

### For Makefile-used variables:
Just update `.env` and re-run the make target:
```bash
# Edit .env
vim .env

# Recreate secret with new token
make cf-secret
```

### For YAML-hardcoded values:
1. Update `.env` for documentation
2. Manually edit the YAML file
3. Re-apply to cluster:
```bash
kubectl apply -f k8s/metallb/metallb-config.yaml
```

## Creating Secrets from .env

### Cloudflare Tunnel Token
```bash
source .env
kubectl create secret generic tunnel-token \
  --from-literal=TUNNEL_TOKEN="$CLOUDFLARE_TUNNEL_TOKEN" \
  -n cloudflared
```

### Cloudflare API Token (for cert-manager)
```bash
make cf-secret  # Automatically uses CLOUDFLARE_ZONE_API_TOKEN from .env
```

### Grafana Credentials
Grafana credentials are set in `k8s/monitoring/values.yaml`:
- Username: `admin`
- Password: `admin` (default)

To change the password permanently:
1. Edit `k8s/monitoring/values.yaml` and change `adminPassword: admin` to your desired password
2. Run `make metrics` to apply

Or get the current password:
```bash
kubectl -n monitoring get secret kube-prometheus-stack-grafana \
  -o jsonpath='{.data.admin-password}' | base64 -d && echo
```

## Future Enhancements

Consider using tools like:
- **envsubst** - Replace variables in templates
- **Kustomize** - Manage K8s configs with overlays
- **Helm** - Templated Kubernetes manifests
- **Sealed Secrets** - Encrypted secrets in Git

## Cloudflare Tunnel DNS Routing

To automate DNS records for hostnames routed through the Tunnel (no dashboard edits):

1) Authenticate once locally (creates `~/.cloudflared/cert.pem`):
```bash
cloudflared login
```

2) Route a hostname:
```bash
# Use TUNNEL_NAME or TUNNEL_ID in .env
make tunnel-route HOST=sub.immas.org
```

3) Verify:
```bash
make verify-host HOST=sub.immas.org
```

Notes:
- VPN/corporate DNS can cache or filter; if resolution lags on your Mac, try `dig @1.1.1.1 +short sub.immas.org` or temporarily set Ethernet DNS to Cloudflare.
