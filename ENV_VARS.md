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

## Future Enhancements

Consider using tools like:
- **envsubst** - Replace variables in templates
- **Kustomize** - Manage K8s configs with overlays
- **Helm** - Templated Kubernetes manifests
- **Sealed Secrets** - Encrypted secrets in Git
