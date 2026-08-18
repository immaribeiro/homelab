---
created: 2026-08-16
updated: 2026-08-16
status: active
repo: github.com/immaribeiro/reconstruction-app
url: https://reconstruction.immas.org
---

# 🏚️ House Reconstruction App

Web application for logging everything about the house reconstruction — costs, phases, tasks, workers, documents, photos. All UI in Portuguese.

## Details

| Field | Value |
|-------|-------|
| **Repo** | `~/GitHub/reconstruction` (67+ commits, active) |
| **URL** | https://reconstruction.immas.org (Cloudflare tunnel + ingress, 42h+ uptime) |
| **Deployment** | `k8s/manifests/reconstruction-app.yml` + ArgoCD app in homelab repo |
| **Database** | PostgreSQL 15 (namespace `reconstruction-db`) |
| **Storage** | MinIO (dual-write + daily migration CronJob 02:00, 10Gi PVC) |
| **Stack** | FastAPI · SQLAlchemy/SQLModel · Jinja2 + htmx + Tailwind |
| **CI** | GitHub Actions → GHCR multi-arch (amd64+arm64) |
| **Status** | Deployed & healthy — **DB EMPTY (no real data yet)** |

## Features (built)

- Cost tracking: categories, phases, transactions
- Construction phase timeline + tasks (phase-linked & standalone)
- Worker/contractor directory (IBAN field)
- Document storage (MinIO) + photo gallery with auto-compression
- Architecture file library
- Read-only share links + reminders
- Auth: Bearer + session hybrid

## Recent changes (repo)

- Portuguese translation of all UI templates
- IBAN field on workers
- Fix 401s on PATCH/POST/DELETE (verify_api_key_or_session)
- Costs API test suite
- MinIO integration (dual-write storage, migration tool, CronJob)

## Status 2026-08-16

- App healthy at https://reconstruction.immas.org, but all DB tables are **0 rows**
- Real house docs exist at `~/Documents/Casa` (Escritura, contracts, PDARQ_LICENCIADA.dwg, certificates, insurance, bank) — not yet imported
- Tests: only `tests/test_costs_api.py` (thin coverage across 12 routers)

## Next (planned)

- Import real data (phases/workers/costs from ~/Documents/Casa)
- Expand test coverage
- Feature roadmap TBD with architect agent

## Related

- [[Homelab Infrastructure]] — where this app is deployed
- `~/Documents/Casa` — real house documents (source material)
