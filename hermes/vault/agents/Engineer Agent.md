---
created: 2026-08-16
updated: 2026-08-16
profile: engineer
model: deepseek/deepseek-v4-flash
provider: nous
status: active
---

# 🔧 Engineer Agent

IT systems engineer responsible for the homelab infrastructure — K3s cluster, Lima VMs, Cloudflare tunnels, deployments, and troubleshooting.

## Configuration

| Field | Value |
|-------|-------|
| **Profile** | engineer |
| **Model** | `deepseek/deepseek-v4-flash` (coding model — good for ops) |
| **Provider** | Nous Portal (OAuth) |
| **Cost** | $0.05 in / $0.10 out per 1M tokens (ultra-cheap) |
| **Fallback 0** | `z-ai/glm-5.2` via Nous (better reasoning for complex issues) |
| **Fallback 1** | `lmstudio/google/gemma-4-e4b` (local, free) |
| **Config file** | `~/GitHub/homelab/hermes/profiles/engineer/config.yaml` |
| **SOUL.md** | `~/GitHub/homelab/hermes/profiles/engineer/SOUL.md` |
| **Telegram** | 🔧 Engineer topic (thread 14) |
| **Reasoning** | medium |
| **Max turns** | 200 |
| **Terminal cwd** | `/Users/imma/GitHub/homelab` |
| **Terminal timeout** | 600s (long — for cluster operations) |

## Responsibilities

- **Lima VMs** — start, stop, verify 3-node K3s cluster (control-1, worker-1, worker-2)
- **K3s cluster** — deployments, services, ingresses, storage, secrets
- **ArgoCD GitOps** — app-of-apps pipeline, sync status
- **Cloudflare Tunnels** — DNS routing, external access, TLS
- **MetalLB + NGINX Ingress** — LoadBalancer IPs (192.168.105.50-99), HTTP routing
- **cert-manager** — wildcard Let's Encrypt certs via Cloudflare DNS-01
- **Monitoring** — Prometheus, Grafana, Alertmanager health
- **Recovery** — post-reboot cluster bring-up, troubleshooting failing pods
- **Backups** — backup.sh script, recovery procedures

## Key Recovery Procedure

```bash
# After Mac Mini reboot (full recovery):
make post-reboot

# Manual steps:
make start-vms
make kubeconfig
make verify-cluster

# Restart Cloudflare Tunnel if needed:
kubectl -n cloudflared rollout restart deploy/cloudflared
```

## Toolset Restrictions

Disabled: `tts`, `image_gen`, `video`, `video_gen`
Keeps: `terminal` (essential), `file`, `web`, `browser`, `code_execution`, `memory`, `cronjob`

## Why Qwen3 Coder 30B?

The engineer needs to run shell commands (kubectl, limactl, make) and understand their output. Qwen3 Coder is:
- Ultra-cheap ($0.06/$0.22) — infrastructure work can be token-heavy
- Good at reading logs and error messages
- Falls back to GLM 5.2 ($0.25/$0.77) for complex multi-step troubleshooting
- 200 max turns (double the backend agent) — cluster operations need more steps

## Command Aliases

```bash
engineer chat          # start interactive chat
engineer doctor        # health check
engineer config set …  # change settings
```

## Related

- [[Agent Overview]]
- [[Telegram Routing]]
- [[Homelab Infrastructure]] — the infrastructure this agent manages
- [[ADR-001 Architecture Review]] — known gaps and roadmap
