---
created: 2026-08-16
updated: 2026-08-21
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

- **2026-08-21 (frontend agent):** Complete UI redesign — light warm design system (terracotta accent #E8590C, warm paper bg, Inter+Sora), sidebar nav with SVG icons, toasts/confirm dialogs, skeleton loaders, responsive mobile nav. All 10 pages rewritten; same routes/API contracts; new app/static/app.js + rebuilt style.css. Commits 85cf768.
- **2026-08-21 (backend agent):** iCloud dataless guard in import script — import aborts (or --force skips) dataless placeholders instead of storing empty bytes; new scripts/check_dataless.py + 3 tests. Commit f1d4e1a. **Blocker: all 121 files in ~/Documents/Casa are iCloud dataless (0B on disk) — materialize on the Mac (brctl download / sudo fileproviderctl repair) then check_dataless.py → import.**
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
