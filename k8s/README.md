# Kubernetes Manifests

This directory contains layered manifests and component-specific configuration applied to the K3s cluster.

## Structure
- `manifests/` – Application-level resources (Deployments, Services, Ingress). Example: `home.yml`, `home-ingress.yaml`.
- `metallb/` – MetalLB address pool + L2 advertisement (`metallb-config.yaml`).
- `cert-manager/` – ACME ClusterIssuers and wildcard certificates.
- `cloudflared/` – Cloudflare Tunnel Deployment, ConfigMap, and README.

## Apply Order (Bootstrapping)
1. MetalLB controller (remote manifest) + `metallb/metallb-config.yaml`
2. cert-manager core manifest (remote) + `cert-manager/clusterissuers.yaml`
3. Cloudflare API token secret (Makefile target `cf-secret`)
4. Wildcard certificate request (`certificate-wildcard-default-namespace.yaml`)
5. Ingress controller (NGINX) – remote manifest
6. Tunnel (`cloudflared/tunnel.yaml`)
7. App manifests (`manifests/`)

## Wildcard TLS
The certificate secret `wildcard-lab-immas-org-tls` is reusable by Ingresses in the same namespace. For a different namespace, create an additional `Certificate` resource or copy the secret (not recommended; prefer new Certificate).

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

### Home App
Simple nginx for testing:
- **Manifest:** `manifests/home.yml`, `manifests/home-ingress.yaml`
- **Access:** https://home.immas.org
- **Deploy:** `make deploy-home`

## Conventions
- Use explicit `ingressClassName: nginx`.
- Keep labels consistent: `app: <name>` used by selectors.
- Separate concerns: networking add-ons vs application manifests.
- All apps use Cloudflare Tunnel (no direct TLS termination on ingress).
