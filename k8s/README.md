# Kubernetes Manifests

This directory contains layered manifests and component-specific configuration applied to the K3s cluster. It now includes a monitoring stack and the Homepage dashboard in addition to core apps.

## Structure
- `manifests/` – Application-level resources (Deployments, Services): `home.yml`, `home-assistant.yml`, `plex.yml`, `qbittorrent.yml`, `traefik-lb.yaml`.
- `metallb/` – MetalLB address pool + L2 advertisement (`metallb-config.yaml`).
- `cert-manager/` – ACME ClusterIssuers and wildcard certificates + wildcard cert requests.
- `cloudflared/` – Cloudflare Tunnel Deployment + routing ConfigMap.
- `monitoring/` – Helm values + dashboards for Prometheus / Grafana.

## Namespaces
Cluster workloads are isolated by namespace for clearer lifecycle management and RBAC.

| Namespace | Purpose | Key Workloads / Objects | Manifest / Source |
|-----------|---------|-------------------------|-------------------|
| `metallb-system` | LoadBalancer IP assignment (L2 mode) | MetalLB controller & speaker | Remote install + `metallb/metallb-config.yaml` |
| `cert-manager` | ACME certificate automation (DNS-01 via Cloudflare) | cert-manager deployments, ClusterIssuers, wildcard cert secrets | Remote install + `cert-manager/clusterissuers.yaml`, `cert-manager/certificate-wildcard*.yaml` |
| `cloudflared` | Private outbound tunnel to Cloudflare edge | `cloudflared` Deployment, Tunnel ConfigMap, credentials Secret | `cloudflared/tunnel.yaml` |
| `ingress-nginx` | Ingress Controller for HTTP routing | `ingress-nginx-controller` Service (LoadBalancer) | Remote manifest (Makefile target `ingress-nginx`) |
| `kube-system` | Core K3s / Kubernetes components & optional Traefik LB Service | Traefik LB (if applied), system pods | `manifests/traefik-lb.yaml` |
| `home-assistant` | Home automation platform | Home Assistant Deployment, PVC | `manifests/home-assistant.yml` |
| `homepage` | Central dashboard (gethomepage.dev) | Homepage Deployment, ConfigMap (settings/services/widgets) | `manifests/home.yml` |
| `plex` | Media server | Plex Deployment, PVC, Service | `manifests/plex.yml` |
| `qbittorrent` | Torrent client | qBittorrent Deployment, PVC, Service | `manifests/qbittorrent.yml` |
| `monitoring` | Metrics collection & visualization | kube-prometheus-stack: Prometheus, Alertmanager, Grafana, exporters | Helm chart (Makefile `metrics` target) + `monitoring/values.yaml` + dashboards YAML |

Add a new namespace by including `metadata.namespace` in your manifest or creating a Namespace object explicitly for advanced policies.

## Apply Order (Bootstrapping)
1. MetalLB controller (remote manifest) + `metallb/metallb-config.yaml`
2. cert-manager core manifest (remote) + `cert-manager/clusterissuers.yaml`
3. Cloudflare API token secret (Makefile target `cf-secret`)
4. Wildcard certificate request (`certificate-wildcard.yaml` in cert-manager namespace)
5. Ingress controller (NGINX) – remote manifest
6. Tunnel (`cloudflared/tunnel.yaml`)
7. Monitoring stack (`make metrics`) – installs Prometheus/Grafana (optional position; can be later)
8. App manifests (`manifests/`)

## Wildcard TLS
The certificate secret `wildcard-immas-org-tls` is reusable by Ingresses in the same namespace. For a different namespace, create an additional `Certificate` resource or copy the secret (not recommended; prefer new Certificate).

## Adding a New App
1. Create Deployment + Service in `manifests/`.
2. Create Ingress referencing wildcard TLS secret.
3. Add tunnel ingress rule (ConfigMap `cloudflared-config`).
4. Apply: `kubectl apply -f k8s/manifests/<app>.yml` and its ingress.

## Verification Commands
```bash
kubectl get svc -A | grep LoadBalancer
kubectl get certificates -A
kubectl get ingress -A
kubectl -n cloudflared logs deploy/cloudflared --tail=30
```

## Deployed Applications

### Homepage Dashboard
Unified entry point for the lab (gethomepage.dev) providing search, weather (Braga), grouped service tiles, and links to internal tooling.
- **Namespace:** `homepage`
- **Manifest:** `manifests/home.yml`
- **Config:** Writable `/app/config` via `emptyDir` + initContainer copying ConfigMap.
- **External Access:** `https://home.immas.org`
- **Cloudflare Tunnel:** Host rule defined in `cloudflared/tunnel.yaml` ConfigMap.
- **Notes:** Edit services/widgets/settings by patching the ConfigMap and restarting the Deployment.

### Home Assistant
Deployed in `home-assistant` namespace with:
- **Manifest:** `manifests/home-assistant.yml`
- **Storage:** 5Gi PVC (`home-assistant-config`)
- **Access:** https://ha.immas.org
- **Configuration:**
  - Trusted proxies: K8s pod/service networks (`10.42.0.0/16`, `10.43.0.0/16`)
  - Timezone: `Europe/Lisbon`
  - Image: `ghcr.io/home-assistant/home-assistant:stable`

**Deploy:**
```bash
kubectl apply -f k8s/manifests/home-assistant.yml
```

**Configure trusted proxies:** Edit `/config/configuration.yaml` inside pod:
```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 10.42.0.0/16  # K8s pod network
    - 10.43.0.0/16  # K8s service network
```

**Add to Cloudflare Tunnel:**
- Subdomain: `ha`
- Domain: `immas.org`
- Service: `http://192.168.105.51:80`

### Plex
Media server streaming content.
- **Namespace:** `plex`
- **Manifest:** `manifests/plex.yml`
- **External Access:** https://plex.immas.org (Tunnel host)
- **Persistent Data:** PVC mounted at `/config` (see manifest for size and path).

### qBittorrent
Torrent client for downloads.
- **Namespace:** `qbittorrent`
- **Manifest:** `manifests/qbittorrent.yml`
- **External Access:** https://qb.immas.org
- **Persistent Data:** PVC for configuration/download state.

### Monitoring Stack (Prometheus / Grafana / Alertmanager)
Installed via Helm (`make metrics`).
- **Namespace:** `monitoring`
- **Values:** `monitoring/values.yaml`
- **Dashboards:** Custom cluster & node dashboards (`dashboards-*.yaml`).
- **Grafana Access:** https://grafana.immas.org (Tunnel host). Admin credentials stored in `grafana-admin` Secret (generated during `make metrics`).
- **Prometheus/Alertmanager Internal:** Accessible via cluster DNS (`monitoring-prometheus.monitoring.svc.cluster.local:9090`). External exposure optional via additional ingress/tunnel rules.

### Cloudflare Tunnel
Outbound-only secure access path for all public hostnames.
- **Namespace:** `cloudflared`
- **Manifest:** `cloudflared/tunnel.yaml`
- **Credentials:** Secret `cloudflared-credentials` from `make tunnel`.
- **Routing:** Ingress rules in ConfigMap map `*.immas.org` subdomains to internal services.

## Conventions
- Use explicit `ingressClassName: nginx`.
- Keep labels consistent: `app: <name>` used by selectors.
- Separate concerns: networking add-ons vs application manifests.
- All apps use Cloudflare Tunnel (no direct TLS termination on ingress).

## Updating Documentation
When adding a new application:
1. Create namespace (implicit via manifest or explicit Namespace object).
2. Add Deployment, Service (and PVC if needed) under `manifests/`.
3. Add Cloudflare Tunnel entry in `cloudflared/tunnel.yaml`.
4. (Optional) Add Helm values / dashboards if part of monitoring.
5. Update this README: add namespace purpose and application section.

## Quick Verification Snippets
```bash
# List namespaces with app counts
kubectl get pods -A --no-headers | awk '{print $1}' | sort | uniq -c

# Check Homepage config loaded
kubectl -n homepage exec deploy/homepage -- ls /app/config

# Prometheus targets
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090 &
open http://localhost:9090/targets
```

