# Multi-Agent Profiles Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Configure Hermes multi-agent profiles (main, architect, backend, frontend) with cost-optimized model assignments and local LMStudio fallback, all synced to the homelab git repo.

**Architecture:** Each profile is a fully independent Hermes instance at `~/.hermes/profiles/<name>/` with its own `config.yaml`, `hermes.json`, `.env`, `memories/`, `skills/`, and `sessions/`. Profiles are launched via `hermes --profile <name>` or switched in the desktop app. Config files are symlinked to the homelab repo for version control.

**Tech Stack:** Hermes Agent 0.20.1, Nous Portal (OAuth), OpenAI API, LMStudio (local), Apple M4 Mac Mini 24GB

---

## Current Environment

| Resource | Value |
|----------|-------|
| Machine | Mac Mini M4, 10-core, 24GB RAM |
| Active model | `z-ai/glm-5.2` via Nous ($0.25/$0.77 per 1M) |
| Fallback 0 | `openai/gpt-5.6-luna` ($0.10/$0.60 per 1M) |
| Fallback 1 | `lmstudio/qwen3.5-9b-mlx` (local, free) |
| LMStudio models | `qwen3.5-9b-mlx`, `google/gemma-4-e4b`, `text-embedding-nomic-embed-text-v1.5` |
| Auth providers | Nous Portal (OAuth), OpenAI (API key), OpenAI Codex (OAuth) |
| Delegation model | `gpt-5.6-luna` via OpenAI |
| Existing profiles | None (`~/.hermes/profiles/` doesn't exist yet) |

## Provider & Model Strategy

### Available Providers

| Provider | Auth | Cost Level | Use For |
|----------|------|------------|---------|
| **Nous Portal** (OAuth) | `hermes auth` | Ultra-cheap to premium (324 models) | Default routing — best price/performance |
| **OpenAI** (API key) | `OPENAI_API_KEY` | Mid to premium | Fallback, delegation subagents |
| **LMStudio** (local) | None | Free | Coding, simple tasks, offline fallback |

### Model Assignment Per Agent

| Profile | Primary Model | Provider | Cost (in/out per 1M) | Fallback | Why |
|---------|---------------|----------|----------------------|----------|-----|
| **main** | `z-ai/glm-5.2` | Nous | $0.25 / $0.77 | OpenAI gpt-5.6-luna → LMStudio qwen3.5 | General-purpose conversational agent — keep current config, best balance |
| **architect** | `deepseek/r1-0528` | Nous | $0.40 / $1.72 | `z-ai/glm-5.2` (Nous) | Reasoning model for system design, planning, code review — needs deep thinking |
| **backend** | `qwen/qwen3-coder-30b-a3b` | Nous | $0.06 / $0.22 | LMStudio `qwen3.5-9b-mlx` (local, free) | Dirt-cheap coding model — backend implementation, API work, database schemas |
| **frontend** | `lmstudio/qwen3.5-9b-mlx` | Local | Free | `qwen/qwen3-coder-30b-a3b` (Nous, $0.06/$0.22) → `z-ai/glm-5.2` | Start local (free) for frontend code; fall back to Nous if local model struggles |

### Cost Projection (estimated daily usage)

| Agent | Est. tokens/day | Cost/day | Notes |
|-------|-----------------|----------|-------|
| main | ~50K in / 50K out | ~$0.05 | Light conversational |
| architect | ~30K in / 30K out | ~$0.06 | Occasional deep reasoning |
| backend | ~100K in / 100K out | ~$0.03 | Heavy coding, cheap model |
| frontend | ~100K in / 100K out | $0.00 (local) | Mostly local LMStudio |
| **Total** | ~280K tokens | **~$0.14/day** | vs ~$0.50+/day if all used GLM 5.2 |

### Delegation (subagent) model

Keep `gpt-5.6-luna` via OpenAI for delegation — it's the workhorse for subagent tasks and has good price/performance ($0.10/$0.60). Each profile inherits this delegation config unless overridden.

---

## Proposed Directory Structure

```
~/.hermes/
├── config.yaml          → symlink to ~/GitHub/homelab/hermes/config.yaml (already done)
├── hermes.json          → symlink to ~/GitHub/homelab/hermes/hermes.json (already done)
├── SOUL.md              → symlink (already done)
├── memories/            → symlinked (already done)
├── cron/                → symlinked (already done)
├── .env                 (NOT synced — secrets)
├── auth.json            (NOT synced — tokens)
└── profiles/
    ├── architect/
    │   ├── config.yaml  → symlink to ~/GitHub/homelab/hermes/profiles/architect/config.yaml
    │   ├── hermes.json → symlink to ~/GitHub/homelab/hermes/profiles/architect/hermes.json
    │   ├── .env        (NOT synced — may have profile-specific keys)
    │   ├── memories/   (profile-specific memory)
    │   ├── sessions/   (runtime — NOT synced)
    │   └── state.db    (runtime — NOT synced)
    ├── backend/
    │   └── (same structure)
    └── frontend/
        └── (same structure)
```

**Note:** The `main` agent stays in the default `~/.hermes/` location (no profile needed — it's the default). Only `architect`, `backend`, and `frontend` get profiles.

---

## Step-by-Step Plan

### Task 1: Create profile directories in the repo

**Objective:** Create the directory structure in `~/GitHub/homelab/hermes/profiles/`

**Files:**
- Create: `~/GitHub/homelab/hermes/profiles/architect/`
- Create: `~/GitHub/homelab/hermes/profiles/backend/`
- Create: `~/GitHub/homelab/hermes/profiles/frontend/`

**Step 1:** Create directories

```bash
mkdir -p ~/GitHub/homelab/hermes/profiles/{architect,backend,frontend}/memories
```

**Step 2:** Update `hermes/.gitignore` to cover profile runtime exclusions

Add to `~/GitHub/homelab/hermes/.gitignore`:
```
# Profile runtime data (config.yaml and hermes.json ARE tracked)
profiles/*/state.db*
profiles/*/sessions/
profiles/*/logs/
profiles/*/cache/
profiles/*/.env
profiles/*/auth.json
profiles/*/projects.db
profiles/*/kanban.db*
profiles/*/channel_directory.json
profiles/*/processes.json
```

**Step 3:** Verify directory structure

```bash
ls -R ~/GitHub/homelab/hermes/profiles/
```

---

### Task 2: Create architect profile config

**Objective:** Configure the architect agent — reasoning-focused, uses DeepSeek R1 for deep thinking, with GLM 5.2 fallback.

**Files:**
- Create: `~/GitHub/homelab/hermes/profiles/architect/config.yaml`
- Create: `~/GitHub/homelab/hermes/profiles/architect/hermes.json`

**Step 1:** Write `config.yaml` for architect

```yaml
model:
  default: deepseek/r1-0528
  provider: nous
  base_url: ''
  api_key_env: OPENAI_API_KEY

fallback_providers:
  '0':
    provider: nous
    model: z-ai/glm-5.2
  '1':
    provider: lmstudio
    model: qwen3.5-9b-mlx
    base_url: http://localhost:1234/v1

agent:
  max_turns: 120
  reasoning_effort: high
  tool_use_enforcement: auto
  task_completion_guidance: true
  environment_probe: false
  coding_context: auto

terminal:
  backend: local
  cwd: /Users/imma/GitHub

display:
  interface: cli
  personality: technical

memory:
  memory_enabled: true
  user_profile_enabled: true
  write_approval: false
  memory_char_limit: 2200
  user_char_limit: 1375

delegation:
  model: gpt-5.6-luna
  provider: openai
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY
  max_iterations: 250
  max_concurrent_children: 5
  max_spawn_depth: 1

custom_providers:
  - name: lmstudio
    base_url: http://localhost:1234/v1
    model: qwen3.5-9b-mlx
    models:
      - qwen3.5-9b-mlx
      - google/gemma-4-e4b
```

**Step 2:** Write `hermes.json` for architect (inherits the same provider pool)

```json
{
  "api_providers": {
    "nous": [],
    "openai": [
      {
        "name": "gpt-5.6-luna",
        "model": "gpt-5.6-luna",
        "api_key_env": "OPENAI_API_KEY",
        "reasoning_options": { "type": "medium" }
      }
    ],
    "custom": [
      {
        "name": "qwen3.5-9b-mlx",
        "endpoint": "http://localhost:1234",
        "model_type": "local_llm"
      }
    ]
  },
  "version": "0.1"
}
```

**Step 3:** Create SOUL.md for architect (personality/instructions)

```markdown
You are the Architect agent — a senior systems architect focused on design, planning, and code review. You think deeply about tradeoffs, system boundaries, and long-term maintainability. You prefer thorough analysis before implementation and document your reasoning. You use deep reasoning models and take time to think through problems carefully.
```

---

### Task 3: Create backend profile config

**Objective:** Configure the backend agent — coding-focused, uses ultra-cheap Qwen3 Coder, with local LMStudio fallback.

**Files:**
- Create: `~/GitHub/homelab/hermes/profiles/backend/config.yaml`
- Create: `~/GitHub/homelab/hermes/profiles/backend/hermes.json`
- Create: `~/GitHub/homelab/hermes/profiles/backend/SOUL.md`

**Step 1:** Write `config.yaml` for backend

```yaml
model:
  default: qwen/qwen3-coder-30b-a3b
  provider: nous
  base_url: ''
  api_key_env: OPENAI_API_KEY

fallback_providers:
  '0':
    provider: lmstudio
    model: qwen3.5-9b-mlx
    base_url: http://localhost:1234/v1
  '1':
    provider: nous
    model: z-ai/glm-5.2

agent:
  max_turns: 150
  reasoning_effort: low
  tool_use_enforcement: auto
  task_completion_guidance: true
  environment_probe: false
  coding_context: auto

terminal:
  backend: local
  cwd: /Users/imma/GitHub

display:
  interface: cli
  personality: concise

memory:
  memory_enabled: true
  user_profile_enabled: true
  write_approval: false
  memory_char_limit: 2200
  user_char_limit: 1375

delegation:
  model: gpt-5.6-luna
  provider: openai
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY
  max_iterations: 250
  max_concurrent_children: 10
  max_spawn_depth: 1

custom_providers:
  - name: lmstudio
    base_url: http://localhost:1234/v1
    model: qwen3.5-9b-mlx
    models:
      - qwen3.5-9b-mlx
      - google/gemma-4-e4b
```

**Step 2:** Write `hermes.json` for backend (same structure as architect)

**Step 3:** Write `SOUL.md` for backend

```markdown
You are the Backend agent — a focused implementation engineer specializing in server-side code, APIs, databases, and infrastructure. You write clean, tested code efficiently. You prefer to use local models when possible to save costs. You work fast and iterate on code, writing tests as you go.
```

---

### Task 4: Create frontend profile config

**Objective:** Configure the frontend agent — uses LOCAL LMStudio first (free), with Nous Qwen Coder fallback.

**Files:**
- Create: `~/GitHub/homelab/hermes/profiles/frontend/config.yaml`
- Create: `~/GitHub/homelab/hermes/profiles/frontend/hermes.json`
- Create: `~/GitHub/homelab/hermes/profiles/frontend/SOUL.md`

**Step 1:** Write `config.yaml` for frontend

```yaml
model:
  default: qwen3.5-9b-mlx
  provider: lmstudio
  base_url: http://localhost:1234/v1
  api_key_env: LMSTUDIO_API_KEY

fallback_providers:
  '0':
    provider: nous
    model: qwen/qwen3-coder-30b-a3b
  '1':
    provider: nous
    model: z-ai/glm-5.2

agent:
  max_turns: 150
  reasoning_effort: low
  tool_use_enforcement: auto
  task_completion_guidance: true
  environment_probe: false
  coding_context: auto

terminal:
  backend: local
  cwd: /Users/imma/GitHub

display:
  interface: cli
  personality: concise

memory:
  memory_enabled: true
  user_profile_enabled: true
  write_approval: false
  memory_char_limit: 2200
  user_char_limit: 1375

delegation:
  model: gpt-5.6-luna
  provider: openai
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY
  max_iterations: 250
  max_concurrent_children: 10
  max_spawn_depth: 1

custom_providers:
  - name: lmstudio
    base_url: http://localhost:1234/v1
    model: qwen3.5-9b-mlx
    models:
      - qwen3.5-9b-mlx
      - google/gemma-4-e4b
```

**Step 2:** Write `hermes.json` for frontend

**Step 3:** Write `SOUL.md` for frontend

```markdown
You are the Frontend agent — a UI/UX implementation engineer specializing in React, CSS, accessibility, and user-facing code. You prefer using local models to keep costs at zero. You care about visual polish, responsive design, and clean component architecture.
```

---

### Task 5: Create profile directories and symlinks in ~/.hermes/

**Objective:** Create the runtime profile directories and symlink the config files from the repo.

**Files:**
- Create: `~/.hermes/profiles/architect/`, `~/.hermes/profiles/backend/`, `~/.hermes/profiles/frontend/`

**Step 1:** Create profile directories with subfolders

```bash
for profile in architect backend frontend; do
  mkdir -p ~/.hermes/profiles/$profile/{memories,sessions,logs,cache}
done
```

**Step 2:** Symlink config files from repo to each profile

```bash
for profile in architect backend frontend; do
  REPO=~/GitHub/homelab/hermes/profiles/$profile
  LIVE=~/.hermes/profiles/$profile

  ln -s "$REPO/config.yaml"  "$LIVE/config.yaml"
  ln -s "$REPO/hermes.json"  "$LIVE/hermes.json"
  ln -s "$REPO/SOUL.md"      "$LIVE/SOUL.md"
done
```

**Step 3:** Symlink memories from repo to each profile

```bash
for profile in architect backend frontend; do
  REPO=~/GitHub/homelab/hermes/profiles/$profile/memories
  LIVE=~/.hermes/profiles/$profile/memories

  # Create MEMORY.md and USER.md in repo
  touch "$REPO/MEMORY.md" "$REPO/USER.md"

  # Remove the empty memories dir created in step 1, symlink the repo dir
  rmdir "$LIVE" 2>/dev/null
  ln -s "$REPO" "$LIVE"
done
```

**Step 4:** Copy `.env` to each profile (they need API keys to function)

```bash
for profile in architect backend frontend; do
  cp ~/.hermes/.env ~/.hermes/profiles/$profile/.env
done
```

**Step 5:** Verify symlinks

```bash
for profile in architect backend frontend; do
  echo "=== $profile ==="
  ls -la ~/.hermes/profiles/$profile/config.yaml
  ls -la ~/.hermes/profiles/$profile/hermes.json
  ls -la ~/.hermes/profiles/$profile/SOUL.md
done
```

---

### Task 6: Test each profile

**Objective:** Verify each profile boots correctly and can reach its model.

**Step 1:** Test architect profile

```bash
hermes --profile architect doctor 2>&1 | head -20
```
Expected: ✓ config files found, ✓ API key configured

**Step 2:** Test backend profile

```bash
hermes --profile backend doctor 2>&1 | head -20
```

**Step 3:** Test frontend profile (local model)

```bash
hermes --profile frontend doctor 2>&1 | head -20
```

**Step 4:** Quick chat test for each (single query)

```bash
hermes --profile architect chat -q "What model are you?" 2>&1 | tail -5
hermes --profile backend chat -q "What model are you?" 2>&1 | tail -5
hermes --profile frontend chat -q "What model are you?" 2>&1 | tail -5
```

---

### Task 7: Commit and push to GitHub

**Objective:** Commit all profile configs to the homelab repo.

**Step 1:** Stage and review

```bash
cd ~/GitHub/homelab
git add hermes/profiles/
git status
```

**Step 2:** Verify no secrets in staged files

```bash
git diff --cached | grep -iE '(api_key|secret|token|password).*[=:][^"'"'"']{20,}' | grep -v 'api_key_env\|#' || echo "No secrets found"
```

**Step 3:** Commit and push

```bash
git commit -m "Add multi-agent profiles: architect, backend, frontend

- architect: DeepSeek R1 (reasoning) with GLM 5.2 fallback
- backend: Qwen3 Coder 30B (ultra-cheap coding) with local LMStudio fallback
- frontend: Local LMStudio Qwen 3.5 (free) with Nous Qwen Coder fallback
- Estimated total cost: ~$0.14/day vs ~$0.50+/day all-GLM
- Configs symlinked from ~/.hermes/profiles/ to repo for version control"

git push origin main
```

---

## Open Questions

1. **Should each profile have its own Telegram channel routing?** Currently all platforms route through the default profile. We could configure `architect` to respond in a specific Telegram thread, etc. — but that requires the gateway to be profile-aware. Defer to Phase 3.

2. **Should we load different skill sets per profile?** E.g., the architect doesn't need `image_gen` or `tts`, the frontend agent doesn't need `terminal` access to production. We can tune `agent.disabled_toolsets` per profile in a follow-up.

3. **LMStudio model swapping**: LMStudio can only serve one model at a time (unless using multi-model mode). If the frontend agent is using `qwen3.5-9b-mlx` locally and the backend agent falls back to local too, they'd compete for the same model slot. We should either:
   - Enable LMStudio multi-model mode (loads multiple models simultaneously)
   - Or have the frontend use a different local model (`google/gemma-4-e4b`) than the backend fallback
   
   **Recommendation:** Set frontend to `qwen3.5-9b-mlx` and backend fallback to `google/gemma-4-e4b` to avoid conflicts. Update in Task 3 config.

4. **Do you want the `main` profile to stay as default (no profile needed)?** Currently it's the default `~/.hermes/` config. We could also create a `~/.hermes/profiles/main/` for symmetry, but it would require migrating the existing default config. **Recommendation:** keep main as default, don't create a profile for it.

## Risks & Tradeoffs

- **DeepSeek R1 reasoning latency**: R1 is a reasoning model — responses will be slower (10-30s) but higher quality for architecture decisions. Worth it for the architect agent.
- **Local model quality**: `qwen3.5-9b-mlx` (9B) is smaller than cloud models. Good for simple frontend tasks but may struggle with complex logic. The fallback chain handles this.
- **LMStudio availability**: If LMStudio isn't running, the frontend agent falls back to Nous ($0.06/$0.22). Not free but still very cheap.
- **Profile isolation**: Each profile gets its own sessions and memory. Cross-profile context sharing requires delegation or manual relay. This is by design — agents shouldn't bleed context.
