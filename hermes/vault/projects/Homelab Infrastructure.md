---
created: 2026-08-16
updated: 2026-08-16
status: active
repo: github.com/immaribeiro/homelab
---

# 🏠 Homelab Infrastructure

K3s Kubernetes cluster on Mac Mini M4 (24GB) using Lima VMs, managed with Terraform + Ansible, deployed via ArgoCD GitOps.

## Infrastructure Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Hypervisor | Lima (VZ mode) + socket_vmnet | ARM64 VMs with bridged networking |
| Orchestration | Terraform (null_resource) | VM lifecycle, inventory generation |
| Configuration | Ansible | K3s installation, system setup |
| Kubernetes | K3s | Lightweight: 1 control-plane + 2 workers |
| Networking | MetalLB (L2) + Flannel | LoadBalancer IPs (192.168.105.50-99) + pod networking |
| Ingress | NGINX Ingress + Cloudflare Tunnel | Internal routing + zero-trust external access |
| TLS | cert-manager + Let's Encrypt | Wildcard certs via Cloudflare DNS-01 |
| GitOps | ArgoCD (app-of-apps) | Declarative application deployment |
| Monitoring | kube-prometheus-stack | Prometheus, Grafana, Alertmanager |
| Storage | K3s local-path provisioner | Node-local PVCs (gap: no replication) |

## Deployed Applications

| App | Namespace | Domain | Description |
|-----|-----------|--------|-------------|
| Homepage | `homepage` | home.immas.org | Central dashboard (gethomepage.dev) |
| Home Assistant | `home-assistant` | ha.immas.org | Home automation platform |
| Plex | `plex` | — | Media server |
| qBittorrent | `qbittorrent` | — | Torrent client |
| Jellyfin | — | — | Open-source media server |
| Vaultwarden | — | vault.immas.org | Password manager |
| FileBrowser | — | files.immas.org | Web file manager (20GB) |
| Open WebUI | — | — | LLM chat interface |
| Life Dashboard | — | — | FastAPI + SQLModel personal dashboard |
| Japan Planner | — | — | Trip planning app |
| Reconstruction App | — | — | House reconstruction tracker + PostgreSQL |
| Homelab Bot | — | — | Telegram bot with qBittorrent integration |
| LM Studio (external) | — | — | LLM inference (bare metal, ExternalName svc) |

## Directory Structure (~/GitHub/homelab)

```
homelab/
├── k8s/
│   ├── argocd/          ← GitOps: app-of-apps + per-app ArgoCD configs
│   ├── manifests/       ← App deployments, services, ingresses
│   ├── metallb/         ← LoadBalancer IP pool config
│   ├── cert-manager/    ← TLS certs + cluster issuers
│   ├── cloudflared/      ← Tunnel config + DNS routing
│   └── monitoring/      ← Grafana dashboards + Helm values
├── ansible/
│   ├── playbooks/       ← k3s-install, k3s-reset, system-setup
│   ├── group_vars/      ← Cluster variables
│   └── inventory.yml    ← Generated from Terraform
├── terraform/
│   ├── main.tf          ← VM lifecycle (null_resource)
│   ├── variables.tf     ← Node specs, network config
│   └── inventory.tpl    ← Ansible inventory template
├── lima/
│   ├── templates/       ← VM definitions
│   └── scripts/         ← VM provisioning scripts
├── hermes/              ← Hermes agent configs (see [[Hermes Config]])
│   ├── config.yaml      ← Main agent config
│   ├── profiles/        ← Multi-agent profiles
│   ├── vault/           ← This Obsidian vault
│   └── docs/            ← Telegram routing docs
├── telegram-downloader/ ← Weekly e-book download (cron job)
├── scripts/             ← Backup, health-check, setup scripts
├── Makefile             ← 20+ automation targets
└── docs/adr/            ← Architecture Decision Records
```

## Key Commands

```bash
# Full bootstrap
bash setup.sh
cd terraform && terraform init && terraform apply
cd ../ansible && ansible-playbook -i inventory.yml playbooks/k3s-install.yml

# ArgoCD
make argocd            # install ArgoCD
make argocd-apps      # deploy app-of-apps

# Cluster status
make status-all       # check all services
kubectl get pods -A   # all pods

# Recovery
# See RECOVERY.md for server restart procedures
```

## Known Gaps (from [[ADR-001 Architecture Review]])

| Area | Risk | Status |
|------|------|--------|
| Storage: local-path only | High — data loss if node fails | Open |
| Secrets: plain K8s secrets | Medium — not GitOps-safe | Open |
| Backups: manual only | Medium — recovery time risk | Open |
| Alerting: no receivers | Low — alerts go nowhere | Open |

## Related

- [[ADR-001 Architecture Review]] — full architecture assessment (2025-06-28)
- [[Hermes Config]] — how Hermes configs are synced to this repo
- [[Agent Overview]] — which Hermes agents can work on this project
