# ADR-001: Architecture Review (2025-06-28)

## Status
Accepted

## Context
Initial architecture review of the homelab infrastructure to assess current state, identify strengths, and recommend improvements.

## Current Architecture

### Infrastructure Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Hypervisor** | Lima (VZ mode) + socket_vmnet | ARM64 VMs with bridged networking on Mac Mini M4 |
| **Orchestration** | Terraform (null_resource) | VM lifecycle, inventory generation |
| **Configuration** | Ansible | K3S installation, system setup |
| **Kubernetes** | K3S | Lightweight single-node control plane + 2 workers |
| **Networking** | MetalLB (L2) + Flannel | LoadBalancer IPs (192.168.105.50-99) + pod networking |
| **Ingress** | NGINX Ingress + Cloudflare Tunnel | Internal routing + secure external access |
| **TLS** | cert-manager + Let's Encrypt | Wildcard certs via Cloudflare DNS-01 |
| **GitOps** | ArgoCD (app-of-apps) | Declarative application deployment |
| **Monitoring** | kube-prometheus-stack | Prometheus, Grafana, Alertmanager |
| **Storage** | K3S local-path provisioner | Node-local PVCs |

### Deployed Applications
- Homepage (dashboard)
- Home Assistant
- Plex
- qBittorrent
- Vaultwarden
- FileBrowser
- Open WebUI (LLM chat)
- Telegram bot

## Assessment

### Strengths

1. **Excellent macOS-native tooling** — Lima VZ with socket_vmnet provides production-grade VM networking without Docker Desktop overhead.

2. **Layered IaC approach** — Clear separation: Lima handles VMs, Terraform orchestrates lifecycle, Ansible configures K3S.

3. **Zero-trust external access** — Cloudflare Tunnel eliminates inbound firewall rules; outbound-only connections with edge TLS.

4. **Operational maturity** — Comprehensive Makefile automation, documented recovery procedures, proper namespace isolation.

5. **GitOps-ready** — ArgoCD app-of-apps pattern with automated sync/prune.

6. **Hybrid compute model** — LM Studio runs bare-metal for GPU access, exposed to cluster via ExternalName service.

### Gaps Identified

| Area | Current State | Risk Level |
|------|---------------|------------|
| Storage | Local-path only | **High** — data loss if node fails |
| Secrets | Plain K8s secrets | **Medium** — not GitOps-safe |
| Backups | Manual only | **Medium** — recovery time risk |
| Network Policies | None | **Low** — defense in depth |
| Alerting | No receivers configured | **Low** — alerts go nowhere |

## Decision

### Immediate Actions (Quick Wins)

1. **Configure Alertmanager receivers** — Wire up Telegram for actual alerting
2. **Add resource requests/limits** — Prevent noisy neighbor issues
3. **Enable PodDisruptionBudgets** — For critical apps (Vaultwarden, Homepage)
4. **Automate backups** — Add `make backup` to cron

### Medium-Term Improvements

| Priority | Improvement | Rationale |
|----------|-------------|-----------|
| P1 | **Longhorn** | Replicated storage with built-in backup to S3 |
| P2 | **Sealed Secrets** | Encrypt secrets for safe Git storage |
| P2 | **Velero** | Scheduled cluster-wide backups |

### Future Considerations (If Scaling)

- Separate etcd from control plane
- Talos Linux for immutable node OS
- Loki for log aggregation

## Consequences

**Positive:**
- Clear roadmap for hardening the cluster
- Identified quick wins vs. larger projects
- Documented current state for future reference

**Negative:**
- Storage improvement (Longhorn) requires migration planning
- Some apps may need downtime for PDB implementation

## Verdict

**Production-ready for personal homelab use.** For actual production workloads, prioritize replicated storage and automated backups.

---

*Reviewed by: Architect Agent*  
*Date: 2025-06-28*
