# Bookshelf — E-book Library Web UI Implementation Plan

> **For Hermes:** Use subagent-driven-development to implement this plan task-by-task, dispatching to the configured profile agents (backend / frontend / engineer) per the agent mapping in §9.

**Goal:** Publish the 370-book Telegram e-book library as a polished web app at **https://books.immas.org** — browse covers, search, and download books — with an OPDS feed that future-proofs Kobo e-reader integration, deployed to the K3s cluster and verified end-to-end.

**Architecture:** A custom single-repo app ("bookshelf"): FastAPI backend that scans the flat library folder on the Mac Mini (visible to the cluster via hostPath, same pattern as filebrowser), extracts EPUB metadata + covers at scan time, serves a JSON API, streams downloads, and exposes an OPDS 1.2 catalog (the Kobo path). React + Vite + Tailwind frontend renders a cover grid with search/filter/download. One multi-arch Docker image pushed to GHCR, deployed via a k8s manifest in the homelab repo, routed through the existing Cloudflare tunnel (`books.immas.org` → cluster Service), behind HTTP Basic auth.

**Tech Stack:** Python 3.12 + FastAPI + uvicorn + ebooklib (EPUB metadata/covers) · React 18 + Vite + Tailwind CSS · Docker multi-stage build · GitHub Actions (build.yml → ghcr.io, multi-arch) · K3s + cloudflared tunnel + cert-manager wildcard.

---

## 1. Current Context (verified 2026-08-18)

| Fact | Value | Evidence |
|---|---|---|
| Library | **Already organized into author folders** (~272 dirs, ~358 unique books + 11 in `_duplicates/`), ~1.3 GB under `~/Downloads/ebook-library/PT` on the Mac Mini | `find …` counts, `ls` |
| Formats | 363 `.epub`, 5 `.pdf` (+1 uppercase `.EPUB` fixed in org pass, 1 no-extension junk) | previous scan |
| Cluster | K3s on Lima, 3 nodes **Ready** (aarch64, v1.36.2), kubeconfig OK | `kubectl get nodes` |
| VM access to books | worker-1 sees `/Users/imma/Downloads/ebook-library/PT` | `limactl shell k3s-worker-1 ls …` |
| Tunnel | cloudflared ConfigMap routes hostname → cluster Service directly (**no Ingress needed**); DNS CNAME via `make tunnel-route HOST=…` | `k8s/cloudflared/tunnel.yaml` |
| Custom-app pattern | own repo + `.github/workflows/build.yml` (multi-arch build → `ghcr.io/immaribeiro/<app>:latest`) + k8s manifest in homelab repo + per-namespace `ghcr-secret` pull secret + tunnel rule + homepage link | japan-planner, reconstruction-app |
| Image tooling | Docker Desktop (linux/arm64), buildx v0.31.1, `gh` authed as immaribeiro w/ `write:packages` | `docker buildx version`, `gh auth status` |
| Downloader pipeline | Weekly cron (Sun 07:00) runs `run_downloader.sh` = **download → organize**; `downloader.py` dedupe is **recursive** (whole-tree) since the org pass | `run_downloader.sh:23`, `downloader.py:267-270` |
| Organizer | `telegram-downloader/organize_library.py` (untracked): idempotent, MD5 dedupe → `_duplicates/`, `STEM_FIXUPS` for known files. **Loose end: re-run showed 12 spurious moves** (9 → `_Uncategorized/`, 1 author-spelling churn, 2 `(2)`-edition collision bugs). Being finalized by the sibling org session; **must be verified 0-move before bookshelf ports it.** | dry-run output |

**⚠️ Critical constraint (resolved):** the library is already organized into author folders, and the downloader's dedupe is already recursive — but `organize_library.py` + the pipeline are **uncommitted**, and the organizer still has a 12-move idempotency bug being finalized by the sibling org session. **Gate:** before bookshelf ports the organizer (Task 8b) or the pipeline is committed (Task 8c), re-run the organizer dry-run and require **0 moves**. If the sibling's fix keys don't match current title-only stems (they appear keyed on old filenames), fix with accent-free `STEM_FIXUPS` keys + NFKD normalization + plan/executor `(N)` collision consistency.

---

## 2. Approach Decision

**Build a custom app (recommended).** Matches the established homelab pattern (japan-planner, reconstruction-app, mission-control are all custom), gives full control of the "cool" UI, and makes the OPDS/Kobo path first-class. Turnkey alternatives (Kavita — prettier but heavier and reader-focused; Calibre-web — needs a `metadata.db` built via `calibredb`, dated UI) are listed as fallbacks in §8.

**App name:** `bookshelf` (namespace `books`, repo `~/GitHub/bookshelf`, image `ghcr.io/immaribeiro/bookshelf:latest`). Renameable before Task 1 if user objects.

**Auth:** HTTP Basic, enabled by default in the k8s Deployment via env from a Secret (`BOOKSHELF_AUTH_ENABLED=true`, `BOOKSHELF_USERNAME`, `BOOKSHELF_PASSWORD`). Applies to `/api/*` and `/opds`. The books are from a private channel — they should not be publicly downloadable. Frontend ships a small login screen that stores the base64 credential in localStorage and attaches the `Authorization` header to fetches.

**Why OPDS in v1:** it is the standard Kobo consumption path (Kobo's browser can open an OPDS feed and download books). It's ~100 lines of XML generation. Building it now makes the "send to Kobo" future task a configuration question, not a rebuild.

---

## 3. Repo Layout (new repo `~/GitHub/bookshelf`)

```
bookshelf/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI app: mounts API, OPDS, static frontend
│   │   ├── config.py        # env config (pydantic-settings)
│   │   ├── scanner.py       # recursive scan, file index, rescan loop
│   │   ├── metadata.py      # EPUB OPF parse (title/authors/series/language) + filename fallback
│   │   ├── covers.py        # cover extraction + disk cache
│   │   ├── organizer.py     # port of telegram-downloader/organize_library.py (library owns organizing)
│   │   ├── opds.py          # OPDS 1.2 catalog builder
│   │   └── auth.py          # HTTP Basic dependency (env-gated)
│   ├── tests/
│   │   ├── conftest.py      # fixture: tiny generated EPUBs in tmp dir
│   │   ├── test_metadata.py
│   │   ├── test_scanner.py
│   │   ├── test_api.py
│   │   └── test_opds.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api.js           # fetch wrapper w/ auth header + base URL
│   │   ├── components/BookGrid.jsx, BookCard.jsx, SearchBar.jsx,
│   │   │   AuthorFilter.jsx, BookModal.jsx, LoginScreen.jsx, SortMenu.jsx
│   │   └── index.css        # Tailwind
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js       # dev proxy /api → :8000
│   └── tailwind.config.js
├── Dockerfile               # multi-stage: node:20-alpine build → python:3.12-slim
├── .github/workflows/build.yml   # copy of japan-planner's (multi-arch → ghcr)
├── .gitignore               # node_modules, dist, __pycache__, .venv
├── k8s/bookshelf.yml        # (also mirrored into homelab repo)
└── README.md
```

---

## 4. API Contract (backend must match exactly)

Book id = `sha1(relpath)[:10]`, stable across rescans.

- `GET /api/health` → `{"status":"ok","books":370,"last_scan":"…"}` (also the liveness/readiness probe path)
- `GET /api/books?q=&author=&format=&sort=title|author|added|size&page=1&per_page=48` → `{"total":370,"page":1,"pages":8,"items":[{BookSummary}]}`
  - BookSummary: `{"id","title","author","series","series_index","format","language","size","added","cover":"/api/books/{id}/cover"}`
  - `q` matches case-insensitively against title + author; `author` is an exact filter; `format` ∈ epub|pdf|…
- `GET /api/books/{id}` → BookSummary + `{"path","download":"/api/books/{id}/download"}`
- `GET /api/books/{id}/download` → streaming `FileResponse` with `Content-Disposition: attachment; filename="…"` (RFC 5987 `filename*` for non-ASCII)
- `GET /api/books/{id}/cover` → cached cover JPEG/PNG, or a 404 → frontend shows placeholder
- `GET /api/authors` → `{"authors":[{"name","count"}]}` sorted by count desc
- `GET /api/stats` → `{"total":370,"by_format":{"epub":363,"pdf":5}, "total_bytes":…}`
- `POST /api/rescan` → triggers rescan, returns health payload
- `POST /api/organize` → (auth) runs the organizer (port of `organize_library.py`): moves books into `<Author>/` folders, MD5-dedupes to `_duplicates/`; returns `{"scanned":N,"moves":N,"duplicates":N}`. Auto-run after each scan when `ORGANIZE_ON_SCAN=true` (default true). Organizer skips files modified in the last 120 s (partial downloads).
- `GET /opds` → OPDS 1.2 catalog root (navigation: All books, by Author, Search)
- `GET /opds/books` → acquisition feed of all books (`<link rel="http://opds-spec.org/acquisition" href="/api/books/{id}/download" type="application/epub+zip">`)
- `GET /opds/search?q=` → filtered acquisition feed (Kobo search entry point)
- `GET /` → frontend `index.html` (static mount); SPA fallback → index.html

**OPDS essentials:** XML content-type `application/atom+xml; charset=utf-8`, feed `<id>urn:bookshelf:</id>`, entries need `<title>`, `<author>`, `<updated>`, acquisition links per format. Basic-auth protected like everything else (Kobo prompts for credentials — supported).

---

## 5. Tasks (bite-sized, TDD, sequential)

### Phase 1 — Backend (backend profile agent)

### Task 1: Repo scaffold + test harness

**Objective:** `~/GitHub/bookshelf` created, git-initialized, pytest wired, first failing test exists.

**Files:**
- Create: `~/GitHub/bookshelf/.gitignore`, `backend/requirements.txt` (`fastapi`, `uvicorn[standard]`, `ebooklib`, `python-multipart`, `pydantic-settings`, `httpx` for tests, `pytest`), `backend/tests/conftest.py`

**Step 1:** `mkdir -p ~/GitHub/bookshelf && cd ~/GitHub/bookshelf && git init && python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt`

**Step 2:** `conftest.py` fixture `make_epub(tmp_path, title, authors, series=None, cover=False)` that builds a minimal valid EPUB in a `zipfile` (mimetype, `META-INF/container.xml`, `OEBPS/content.opf` with dc:title/dc:creator/dc:language/calibre:series metas, one `x.html`, optional `cover.jpg`). This fixture is the backbone of all backend tests — get it right.

**Step 3:** Write a placeholder failing test `test_metadata.py::test_title_extracted` asserting `metadata.epub_info(path)["title"] == "O Teste"`.

**Step 4:** Run `.venv/bin/pytest backend/tests -q` — expected FAIL (module not found). Commit `chore: scaffold bookshelf backend + test harness`.

### Task 2: EPUB metadata extraction

**Objective:** `backend/app/metadata.py` parses OPF XML for title, authors, series, series_index, language; filename heuristic fallback for PDFs/no-metadata EPUBs. Reuse the parsing approach from `~/GitHub/homelab/telegram-downloader/organize_library.py` (`NS` dict, `dc:title`, `dc:creator`, `calibre:series`, `calibre:series_index`, `clean_title`) — port the relevant functions (they're proven), don't reinvent. Do NOT port the author-normalization junk filters (AUTHOR_FIXUPS etc.) — keep it simple: take first creator, title-case only if all-caps.

**Files:** Create `backend/app/metadata.py`, extend `backend/tests/test_metadata.py`.

**Steps:** write tests → run (fail) → implement `epub_info(path) -> dict|None` and `filename_info(stem) -> dict` → run (pass). Tests: title, multiple creators (join " & "), series + index, missing metadata → filename fallback, corrupt zip → `None`. Commit `feat: epub metadata extraction`.

### Task 3: Scanner + in-memory index

**Objective:** `backend/app/scanner.py` walks the library recursively, indexes every file with a recognized extension (case-insensitive: `.epub .pdf .mobi .azw3 .cbz`), **skips the `_duplicates/` directory** (and `.DS_Store`, `._*` AppleDouble), builds `BookSummary` dicts (id = sha1(relpath)[:10], size, added = file mtime, metadata via Task 2), ignores no-extension files and junk. Exposes a thread-safe `LibraryIndex` with `search(q, author, format, sort, page, per_page)`, `get(book_id)`, `authors()`, `stats()`.

**Files:** Create `backend/app/scanner.py`, `backend/tests/test_scanner.py`.

**Steps:** tests first (scan fixture dir with 3 epubs + 1 pdf + junk files → counts correct; id stable; search "test" finds title/author matches; author filter exact; sort orders) → implement → pass. Commit `feat: library scanner + index`.

### Task 4: Cover extraction + cache

**Objective:** `backend/app/covers.py` extracts the cover image from an EPUB (prefer the `meta[name="cover"]` id in OPF → manifest href; fallback: first image in the zip) and writes it to the cache dir (config `COVERS_DIR`, default `/data/covers`) as `<book_id>.jpg`. Cache keyed by (mtime, size) — skip extraction when cached file is newer than the book file. PDFs → return None (frontend shows placeholder).

**Files:** Create `backend/app/covers.py`, `backend/tests/test_covers.py`.

**Steps:** tests (cover extracted from fixture epub with cover; no-cover epub → None; cache hit doesn't re-extract) → implement (use Pillow to normalize to JPEG, resize max 600px) → pass. Add `Pillow` to requirements. Commit `feat: cover extraction + cache`.

### Task 5: FastAPI app — health, books, authors, stats

**Objective:** `backend/app/main.py` + `config.py` (pydantic-settings: `LIBRARY_DIR` default `/data/books`, `COVERS_DIR` `/data/covers`, `RESCAN_INTERVAL_SECONDS` 900, `AUTH_ENABLED` false, `AUTH_USERNAME`, `AUTH_PASSWORD`). Lifespan: scan on startup, then `asyncio` background task rescans every interval. Wire the §4 endpoints (all except download/opds/auth).

**Files:** Create `backend/app/main.py`, `backend/app/config.py`, `backend/tests/test_api.py`.

**Steps:** tests via `fastapi.testclient.TestClient` (health 200; books pagination; q filter; author filter; authors list; stats; 404 for unknown id) → implement → pass. Commit `feat: core API`.

### Task 6: Download endpoint

**Objective:** `GET /api/books/{id}/download` streams the file. `FileResponse` with `filename=` (Starlette sets `Content-Disposition` incl. RFC 5987 filename*), correct media type from extension. Test: response 200, `content-length` == file size, header contains the filename.

**Files:** `backend/app/main.py`, `backend/tests/test_api.py`.

**Steps:** test → implement → pass. Commit `feat: book download endpoint`.

### Task 7: OPDS 1.2 feed

**Objective:** `backend/app/opds.py` builds the catalog root, acquisition feed, and search feed per §4, using the index. Must produce valid XML (assert with `xml.etree` parse + content-type header in tests). Acquisition link href points at `/api/books/{id}/download`, type `application/epub+zip` (or `application/pdf`).

**Files:** Create `backend/app/opds.py`, `backend/tests/test_opds.py`.

**Steps:** tests (root has nav links; /opds/books has N entries; entry has title/author/updated/acquisition link; search filters) → implement → pass. Commit `feat: OPDS 1.2 catalog`.

### Task 8: HTTP Basic auth

**Objective:** `backend/app/auth.py` — FastAPI dependency `require_auth`. When `AUTH_ENABLED`, 401 + `WWW-Authenticate: Basic` unless `Authorization: Basic base64(user:pass)` matches (constant-time compare). Applied to all `/api/*`, `/opds*`, and `POST /api/rescan`. Static frontend stays public (it's a login shell). Tests: no creds → 401; wrong → 401; right → 200; disabled → 200.

**Files:** Create `backend/app/auth.py`, update `backend/app/main.py`, `backend/tests/test_api.py`.

**Steps:** test → implement → pass. Commit `feat: HTTP basic auth`.

### Task 8b: Organizer port (bookshelf owns library organization)

**Objective:** `backend/app/organizer.py` — port `~/GitHub/homelab/telegram-downloader/organize_library.py` (the **final, verified 0-move version** — see Task 8c gate) as a module: `organize(library_dir, min_age_seconds=120) -> {"scanned", "moves", "duplicates"}`. Reuse `metadata.py`'s EPUB parsing instead of its internal copy where trivial, but keep the proven heuristics (STRIP_RE, cut_zlib, AUTHOR_FIXUPS, STEM_FIXUPS, `_duplicates/` staging, `(2)` collision handling) verbatim. Wire `POST /api/organize` (auth) and auto-run after each scan when `ORGANIZE_ON_SCAN=true` (default true — after organize, re-scan so the index reflects moves). Add `ORGANIZE_ON_SCAN` to `config.py`.

**Files:** Create `backend/app/organizer.py`, `backend/tests/test_organizer.py`, update `backend/app/main.py`, `backend/app/config.py`.

**Steps:** tests (organize fixture dir: moves file into author folder; dedupes MD5 copies into `_duplicates/`; skips file with fresh mtime; idempotent — second run = 0 moves; `POST /api/organize` requires auth, returns report) → port + implement → pass. Commit `feat: library organizer + /api/organize`.

### Task 8c: Finalize + commit the homelab downloader pipeline (gate: 0 moves)

**Objective:** pick up the sibling session's loose ends in `~/GitHub/homelab/telegram-downloader/`. Steps:
1. Re-run `.venv/bin/python organize_library.py --dir /Users/imma/Downloads/ebook-library/PT` (dry-run) — **must report `moves: 0`**. If the current `STEM_FIXUPS` keys don't match (they appear keyed on pre-org filenames like `"sete breves licoes de fisica carlo r"` while current stems are title-only), fix: NFKD-normalize `stem_key` (strip diacritics via `unicodedata`) and use accent-free keys matching title-only stems; make `plan_organization` apply the same `(N)` collision logic as the executor so `(2)`-edition files become `[keep]`.
2. `git add telegram-downloader/organize_library.py telegram-downloader/downloader.py telegram-downloader/run_downloader.sh` → commit `feat(telegram-downloader): recursive dedupe + organize pipeline (finalized organizer)`.
3. Confirm `run_downloader.sh` still execs cleanly (`bash -n`).

**Gate:** do NOT port (Task 8b) from an unverified copy — the file must be 0-move idempotent first.

**Backend done when:** `.venv/bin/pytest backend/tests -q` → all green; `.venv/bin/uvicorn backend.app.main:app --port 8000` with `LIBRARY_DIR=~/Downloads/ebook-library/PT` serves /api/health with `"books":N` (N ≈ 358, the real count — print it, don't hardcode 370).

---

### Phase 2 — Frontend (frontend profile agent)

### Task 9: Vite + Tailwind scaffold

**Objective:** `frontend/` created with `npm create vite@latest . -- --template react`, Tailwind v3 installed (`npm i -D tailwindcss postcss autoprefixer`, `npx tailwindcss init -p`), `vite.config.js` dev proxy `/api` → `http://localhost:8000`. Dark theme baseline in `index.css` (slate-900 bg, indigo accent — match the homelab dashboard aesthetic).

**Steps:** scaffold → `npm run build` passes → commit `chore: frontend scaffold`.

### Task 10: API client + cover grid

**Objective:** `api.js` (fetch wrapper: base `/api`, attaches `Authorization: Basic …` from localStorage `bookshelf-auth` when present, JSON + error handling) + `BookGrid`/`BookCard` rendering the cover grid from `/api/books` (48/page, infinite scroll or "load more" button — keep it simple: load-more). Card: cover (lazy `loading="lazy"`), title, author, format badge. Loading skeleton + empty state.

**Files:** `frontend/src/api.js`, `App.jsx`, `components/BookGrid.jsx`, `BookCard.jsx`.

**Steps:** implement against `npm run dev` + local backend → `npm run build` passes → commit `feat: cover grid`.

### Task 11: Search, author filter, sort

**Objective:** `SearchBar` (debounced 300ms → `q`), `AuthorFilter` (dropdown from `/api/authors`, "All authors" default), `SortMenu` (title/author/size). State in `App.jsx` (query params pushed to `history.replaceState` so refresh keeps filters).

**Files:** `components/SearchBar.jsx`, `AuthorFilter.jsx`, `SortMenu.jsx`, `App.jsx`.

**Steps:** implement → build → commit `feat: search, author filter, sort`.

### Task 12: Book detail modal + download

**Objective:** Click card → `BookModal` (fetch `/api/books/{id}`): larger cover, full title, author, series + index, language, format, size, "Download" button → opens `/api/books/{id}/download` (auth header caveat: `<a href>` can't send headers — use `fetch` → blob → `URL.createObjectURL` download, or append `?token=` — **decision: use fetch→blob**, simplest and works with Basic auth). Esc/backdrop closes.

**Files:** `components/BookModal.jsx`, `App.jsx`.

**Steps:** implement → build → commit `feat: book detail + download`.

### Task 13: Login screen

**Objective:** On first load, if any API call 401s (or if `bookshelf-auth` absent), show `LoginScreen` (username/password) → store `btoa(user:pass)` → retry. Logout button in header.

**Files:** `components/LoginScreen.jsx`, `api.js`, `App.jsx`.

**Steps:** implement → build → commit `feat: login screen`.

### Task 13b: Organize-library button

**Objective:** header action "Organize" (icon `mdi-folder-refresh`) calling `POST /api/organize` (auth) → show result toast/alert (`Moved: N · Duplicates: N · Scanned: N`) and reload the grid. Disabled while a run is in flight. This is the user-facing hook for the future "organize as we download" flow — keep it visible but unobtrusive (secondary button next to logout).

**Files:** `components/OrganizeButton.jsx`, `App.jsx`, `api.js`.

**Steps:** implement → build → commit `feat: organize library button`.

### Task 14: Polish + responsive

**Objective:** responsive grid (2/3/4/5 cols by breakpoint), sticky header w/ title + search + count, focus/empty states, page title/favicon, mobile-safe modal, minor animations (hover lift). Verify in browser against live backend.

**Steps:** implement → `npm run build` → commit `feat: polish and responsiveness`.

---

### Phase 3 — Packaging, CI, deploy (engineer profile agent)

### Task 15: Multi-stage Dockerfile + GHCR workflow

**Objective:** `Dockerfile`:

```dockerfile
# --- build frontend ---
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# --- runtime ---
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /build/dist ./app/static
ENV LIBRARY_DIR=/data/books COVERS_DIR=/data/covers
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`frontend/vite.config.js` must build with `base: '/'` and the app must read static files from `app/static` (point FastAPI's `StaticFiles` there, mount at `/`, `html=True`, SPA fallback via `StaticFiles(html=True)`).

Copy `.github/workflows/build.yml` from `~/GitHub/japan-planner` (identical: multi-arch amd64/arm64, push latest on main).

**Steps:** local `docker build --platform linux/arm64 -t ghcr.io/immaribeiro/bookshelf:latest .` succeeds; run container locally with `-v ~/Downloads/ebook-library/PT:/data/books:ro -e AUTH_ENABLED=false -p 8000:8000`, `curl localhost:8000/api/health` shows 370 books → `git init` repo, create GitHub repo (`gh repo create immaribeiro/bookshelf --private --source=. --push`), push → workflow builds and pushes image. Verify image exists: `gh api /users/immaribeiro/packages/container/bookshelf` (or `docker manifest inspect ghcr.io/immaribeiro/bookshelf:latest`). Commit.

### Task 16: k8s manifest + pull secret

**Objective:** `k8s/bookshelf.yml` in the **homelab repo** (`~/GitHub/homelab/k8s/manifests/bookshelf.yml`), modeled on filebrowser.yml + japan-planner.yml:

```yaml
apiVersion: v1
kind: Namespace
metadata: { name: books }
---
apiVersion: v1
kind: Secret
metadata: { name: bookshelf-auth, namespace: books }
type: Opaque
stringData:
  BOOKSHELF_AUTH_ENABLED: "true"
  BOOKSHELF_USERNAME: "imma"
  BOOKSHELF_PASSWORD: "<generated>"   # openssl rand -base64 24
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: bookshelf-covers, namespace: books }
spec:
  accessModes: [ReadWriteOnce]
  resources: { requests: { storage: 1Gi } }
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: bookshelf, namespace: books, labels: { app: bookshelf } }
spec:
  replicas: 1
  strategy: { type: Recreate }
  selector: { matchLabels: { app: bookshelf } }
  template:
    metadata: { labels: { app: bookshelf } }
    spec:
      imagePullSecrets: [{ name: ghcr-secret }]
      containers:
        - name: bookshelf
          image: ghcr.io/immaribeiro/bookshelf:latest
          ports: [{ containerPort: 8000, name: http }]
          envFrom: [{ secretRef: { name: bookshelf-auth } }]
          env:
            - { name: LIBRARY_DIR, value: /data/books }
            - { name: COVERS_DIR, value: /data/covers }
            - { name: ORGANIZE_ON_SCAN, value: "true" }
          volumeMounts:
            - { name: library, mountPath: /data/books }   # RW: bookshelf owns organization
            - { name: covers, mountPath: /data/covers }
          resources:
            requests: { cpu: 100m, memory: 128Mi }
            limits:   { cpu: 500m, memory: 512Mi }
          livenessProbe:  { httpGet: { path: /api/health, port: http }, initialDelaySeconds: 15, periodSeconds: 30 }
          readinessProbe: { httpGet: { path: /api/health, port: http }, initialDelaySeconds: 5,  periodSeconds: 10 }
      volumes:
        - { name: library, hostPath: { path: /Users/imma/Downloads/ebook-library, type: Directory } }
        - { name: covers, persistentVolumeClaim: { claimName: bookshelf-covers } }
---
apiVersion: v1
kind: Service
metadata: { name: bookshelf, namespace: books, labels: { app: bookshelf } }
spec:
  type: ClusterIP
  ports: [{ port: 80, targetPort: http, protocol: TCP, name: http }]
  selector: { app: bookshelf }
```

> ⚠️ **RW mount note:** the library volume is mounted read-write so the app can organize. `organizer.py` skips files modified in the last 120 s, and `ORGANIZE_ON_SCAN` is safe because the organizer is 0-move idempotent on a stable library. The weekly host cron also runs its own organize pass — both are idempotent and coexist.

**Steps:** create `ghcr-secret` in `books` ns (`kubectl -n books create secret docker-registry ghcr-secret --docker-server=ghcr.io --docker-username=immaribeiro --docker-password="$(gh auth token)"`) → apply manifest (apply twice if namespace race: `kubectl apply -f k8s/manifests/bookshelf.yml` ×2) → `kubectl -n books rollout status deploy/bookshelf` → pod Running; `kubectl -n books logs deploy/bookshelf` shows scan complete, no errors. Commit to homelab repo.

### Task 17: Tunnel route + DNS + homepage

**Objective:** make `books.immas.org` live.

**Steps:**
1. `kubectl apply -f k8s/cloudflared/tunnel.yaml` after adding to the ConfigMap in that file:
   ```yaml
   - hostname: books.immas.org
     service: http://bookshelf.books.svc.cluster.local:80
   ```
2. Update the **live** ConfigMap (create with `--from-literal=config.yaml='<full yaml>' --dry-run=client -o yaml | kubectl apply -f -`) and `kubectl -n cloudflared rollout restart deploy/cloudflared`.
3. DNS: `cd ~/GitHub/homelab && make tunnel-route HOST=books.immas.org` (uses TUNNEL_ID from `.env`; verify `dig +short books.immas.org`).
4. Add a Books card to `k8s/manifests/home.yml` services.yaml (Media or Apps section):
   ```yaml
   - Books:
       href: https://books.immas.org
       icon: mdi-book-open-variant
       description: E-book Library
   ```
   Re-apply homepage ConfigMap (`kubectl -n homepage rollout restart deploy/homepage` after applying).
5. Commit homelab repo changes (tunnel.yaml + home.yml).

### Task 18: End-to-end verification

**Objective:** full E2E green. Run the §7 checklist; fix anything failing (report to orchestrator if the fix spans another profile's code).

**Steps:**
1. `curl -s https://books.immas.org/api/health` → `{"status":"ok","books":370,…}`
2. `curl -s -u imma:<pass> "https://books.immas.org/api/books?q=sombra"` → results contain J.R. Ward books
3. No creds → `curl -s -o /dev/null -w "%{http_code}" https://books.immas.org/api/books` → 401
4. Cover: `curl -s -o /tmp/c.jpg -u … https://books.immas.org/api/books/<id>/cover` → valid JPEG (`file /tmp/c.jpg`)
5. Download integrity: `curl -sL -u … "https://books.immas.org/api/books/<id>/download" -o /tmp/b.epub && stat -f%z /tmp/b.epub` equals the API-reported size, and `unzip -t /tmp/b.epub` passes
6. OPDS: `curl -s -u … https://books.immas.org/opds | python3 -c "import sys,xml.etree.ElementTree as ET; ET.fromstring(sys.stdin.read()); print('valid XML')"`
7. Frontend: browser (or `curl -s https://books.immas.org/ | grep -i '<div id="root">'`) loads; login works; grid shows covers
8. Homepage: https://home.immas.org shows the Books card
9. Tunnel stability: `kubectl -n cloudflared logs deploy/cloudflared | tail -5` shows registered connections
10. Update the Obsidian note `hermes/vault/projects/Telegram E-book Downloader.md` (add "Library web UI" section pointing to books.immas.org + repo) — commit. (Use homelab-vault-sync skill if needed.)

---

## 6. Files That Change

**New repo `~/GitHub/bookshelf`:** everything in §3 (backend, frontend, Dockerfile, workflow, README).

**Homelab repo (`~/GitHub/homelab`):**
- Add: `k8s/manifests/bookshelf.yml`
- Modify: `k8s/cloudflared/tunnel.yaml` (ingress rule), `k8s/manifests/home.yml` (homepage card)
- Modify: `hermes/vault/projects/Telegram E-book Downloader.md` (project note)
- Possibly: `hermes/cron/jobs.json` (only if user opts into the organizer + downloader patch — see §8)

**Untouched:** `telegram-downloader/*` (unless §8 option chosen), `~/Downloads/ebook-library/PT` (read-only for the app).

---

## 7. Verification Checklist (final gate)

- [ ] `pytest backend/tests` all green (backend profile)
- [ ] `npm run build` green (frontend profile)
- [ ] `docker manifest inspect ghcr.io/immaribeiro/bookshelf:latest` resolves (arm64)
- [ ] `kubectl -n books get pods` → Running; logs show real book count (~358) scanned, no tracebacks
- [ ] `https://books.immas.org/api/health` → real book count, requires auth (401 without)
- [ ] Cover thumbnails render for EPUBs; PDFs show placeholder
- [ ] Download of a book → byte-identical to the file on disk (`cmp` against `~/Downloads/ebook-library/PT/…`)
- [ ] `/opds` valid XML; acquisition link downloads the book
- [ ] `POST /api/organize` → `{"scanned":N,"moves":0,"duplicates":0}` on the stable library (idempotent)
- [ ] `organize_library.py` dry-run in telegram-downloader reports `moves: 0`; pipeline committed
- [ ] `https://home.immas.org` shows the Books card
- [ ] Weekly cron still runs clean next Sunday (no re-download storm)
- [ ] Homelab repo committed & pushed; bookshelf repo pushed with workflow badge

---

## 8. Risks, Tradeoffs, Open Questions

1. **Organization (resolved).** The library is already organized into author folders by the sibling session; the downloader dedupe is already recursive, so no re-download risk. Remaining: the organizer's 12-move idempotency bug (Task 8c gate) and committing the pipeline. **Bookshelf owns ongoing organization** (`/api/organize` + auto-run on scan, RW mount); the host cron pipeline runs its own idempotent organize pass — both coexist.
2. **Turnkey fallback.** If the custom build stalls, Kavita (`kavitap/kavita`, folder-scan + OPDS, prettier out of the box, heavier ~1GB RAM) or Calibre-web (needs `calibredb` one-shot to build `metadata.db` from the folder) are drop-in alternatives for the same tunnel/DNS work. Only the manifest + image change.
3. **Auth ergonomics.** HTTP Basic + fetch→blob download is simple and robust but means no per-device sessions; fine for a 1-user library. Cloudflare Access (Zero Trust) is the upgrade path and works with the tunnel — defer.
4. **Kobo (future phase, enabled by design).** OPDS is live in v1: on a Kobo, open browser → `https://books.immas.org/opds` → enter credentials → browse/download. "Send to Kobo" (email-to-Kobo Cloud / USB transfer / Calibre wireless) is a follow-up feature, no architecture change needed.
5. **Cover cache freshness.** Cache keyed by mtime+size; if the downloader overwrites a file with same size, cover may go stale — acceptable; `POST /api/rescan` + pod restart clears it.
6. **hostPath scheduling.** All Lima VMs mount the Mac home (verified on worker-1), so any node works; no nodeSelector needed. If a future node lacks the mount, add `nodeSelector` pinning to a VM with the mount.
7. **App name** ("bookshelf") is changeable before Task 1; user veto overrides.
8. **Single replica / no HA** — consistent with the rest of the homelab (Recreate strategy, 1 replica).

---

## 9. Agent Assignment & Sequencing

| Phase | Owner | Deliverable |
|---|---|---|
| Design/review | main (this session) | this plan |
| Tasks 1–8 (backend) | **backend** profile agent (via delegate_task, sequential or 2 at a time) | FastAPI app + green pytest |
| Tasks 9–14 (frontend) | **frontend** profile agent (can run in parallel with backend once the API contract §4 is fixed) | React app + green build |
| Tasks 15–17 (CI/deploy) | **engineer** profile agent (needs Tasks 1–14 merged, i.e. after both) | image on GHCR, app live at books.immas.org |
| Task 18 (E2E) | main + engineer | checklist green, docs updated |

**Execution model:** subagent-driven-development — one delegate_task per task (or per small group) with the task text + §4 contract + §1 context injected; spec-compliance review then code-quality review after each; integrate into `~/GitHub/bookshelf` (backend and frontend can work in the same repo sequentially or on branches merged by main). Engineer profile has autonomy for infra ops (its configured profile grants that). After Task 18, report to user with the URL, credentials location (k8s secret, `kubectl -n books get secret bookshelf-auth`), and the Kobo how-to.

**Definition of done:** §7 checklist all checked, both repos pushed, project note updated.
