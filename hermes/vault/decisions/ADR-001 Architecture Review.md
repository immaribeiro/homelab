---
created: 2026-08-16
updated: 2026-08-16
status: accepted
date: 2025-06-28
reviewer: Architect Agent
---

# ADR-001: Architecture Review (2025-06-28)

> Original: `docs/adr/001-architecture-review-2025-06-28.md` in the homelab repo

## Status

Accepted

## Context

Initial architecture review of the homelab infrastructure to assess current state, identify strengths, and recommend improvements.

## Assessment

### Strengths

1. **Excellent macOS-native tooling** — Lima VZ with socket_vmnet provides production-grade VM networking without Docker Desktop overhead
2. **Layered IaC approach** — Lima (VMs) → Terraform (lifecycle) → Ansible (config) → K3s (orchestration)
3. **Zero-trust external access** — Cloudflare Tunnel eliminates inbound firewall rules; outbound-only with edge TLS
4. **Operational maturity** — Makefile automation, recovery procedures, namespace isolation
5. **GitOps-ready** — ArgoCD app-of-apps with automated sync/prune
6. **Hybrid compute** — LM Studio bare-metal for GPU, exposed to cluster via ExternalName

### Gaps

| Area | Current | Risk | Proposed Fix |
|------|---------|------|-------------|
| Storage | local-path only | **High** | Longhorn (replicated + S3 backup) |
| Secrets | Plain K8s secrets | **Medium** | Sealed Secrets |
| Backups | Manual | **Medium** | Velero (scheduled) |
| Alerting | No receivers | **Low** | Wire Alertmanager → Telegram |

## Decisions

### Quick Wins
1. Configure Alertmanager → Telegram alerts
2. Add resource requests/limits on all pods
3. Enable PodDisruptionBudgets for critical apps
4. Automate backups via `make backup` cron

### Medium-Term
- **P1:** Longhorn for replicated storage
- **P2:** Sealed Secrets for GitOps-safe secrets
- **P2:** Velero for cluster-wide backups

### Future (If Scaling)
- Separate etcd from control plane
- Talos Linux for immutable node OS
- Loki for log aggregation

## Verdict

**Production-ready for personal homelab use.** Prioritize replicated storage and automated backups for production workloads.

## Related

- [[Homelab Infrastructure]] — current state of the cluster
