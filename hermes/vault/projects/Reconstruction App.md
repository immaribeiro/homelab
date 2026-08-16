---
created: 2026-08-16
updated: 2026-08-16
status: active
repo: github.com/immaribeiro/reconstruction-app
---

# 🏚️ House Reconstruction App

Web application for tracking house reconstruction progress. Deployed on the K3s cluster with PostgreSQL.

## Details

| Field | Value |
|-------|-------|
| **Repo** | `~/GitHub/reconstruction` (67 commits) |
| **Last activity** | 2026-03-29 |
| **Deployment** | `k8s/manifests/reconstruction-app.yml` in homelab repo |
| **Database** | PostgreSQL (separate deployment: `reconstruction-db`) |
| **GitOps** | ArgoCD app: `k8s/argocd/apps/reconstruction-app.yaml` |
| **Secrets** | MinIO credentials + imagePullSecrets configured |
| **Status** | Active |

## Recent Changes

- Add MinIO credentials to reconstruction-app secret
- Add imagePullSecrets for reconstruction-app
- Add reconstruction-app deployment + ArgoCD app
- Deploy PostgreSQL database for House Reconstruction Management application

## Related

- [[Homelab Infrastructure]] — where this app is deployed
