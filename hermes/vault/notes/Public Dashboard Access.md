---
created: 2026-08-16
updated: 2026-08-16
tags: [hermes, dashboard, cloudflare, tunnel, oauth]
---

# 🌐 Public Dashboard Access

The Hermes dashboard on the Mac Mini is publicly reachable at:

**https://hermes.immas.org**

Sign in with your **Nous Portal account** (or the basic-auth username/password fallback).

## How It Works

```
Browser (anywhere)                          Mac Mini (imma-mini)
        │                                          │
  https://hermes.immas.org                        hermes dashboard :9119
        │                                          │ (launchd: ai.hermes.dashboard)
   Cloudflare edge ──► Cloudflare Tunnel ──► http://192.168.8.161:9119
   (TLS, *.immas.org cert)   (cloudflared pod in k8s)
```

- **Tunnel:** the `cloudflared` deployment in the k3s cluster routes `hermes.immas.org` → `http://192.168.8.161:9119` (ingress rule in `k8s/cloudflared/tunnel.yaml`)
- **DNS:** CNAME `hermes.immas.org` → tunnel UUID `7725b3d6-…` (added via `cloudflared tunnel route dns`)
- **Auth:** Nous Portal OAuth — dashboard registered with redirect URI `https://hermes.immas.org/auth/callback`
- **Public URL override:** `dashboard.public_url: https://hermes.immas.org` (so OAuth callbacks + Host-header guard resolve to the public URL)

## Config (on the Mac Mini)

| Setting | Location | Value |
|---------|----------|-------|
| OAuth client ID | `~/.hermes/.env` (`HERMES_DASHBOARD_OAUTH_CLIENT_ID`) + `config.yaml` `dashboard.oauth.client_id` | `agent:cmsw4ufm7007nho0as0osc2zn` |
| Public URL | `config.yaml` `dashboard.public_url` | `https://hermes.immas.org` |
| Auth providers | — | `basic` + `nous` |

> Note: an earlier client ID (`agent:cmsw46h76003oi909lp07qe60`, generated on the portal Local Dashboards page) was superseded by the CLI registration with the public redirect URI. It can be revoked at https://portal.nousresearch.com/local-dashboards.

## Verification

```bash
curl -s https://hermes.immas.org/api/status | jq '.auth_required, .auth_providers'
# true
# ["basic", "nous"]
```

## Maintenance

- **Restart dashboard** (after config changes): `launchctl kickstart -k gui/$(id -u)/ai.hermes.dashboard`
- **Restart tunnel** (after ingress changes): `kubectl -n cloudflared rollout restart deploy/cloudflared`
- **Revoke access:** https://portal.nousresearch.com/local-dashboards
- **Remove the public route:** delete the ingress rule from `k8s/cloudflared/tunnel.yaml`, delete the DNS CNAME

## Related

- [[Hermes Config]]
- [[Agent Overview]]
- [[Homelab Infrastructure]]
