---
created: 2026-08-18
updated: 2026-08-21
---

# 📚 Skills Library

Agent skills installed across the Hermes fleet, distilled/ported from [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) (Apache-2.0, cloned at `~/GitHub/awesome-llm-apps`). All skills are markdown `SKILL.md` files with YAML frontmatter — load via `skill_view`.

## Main profile (`~/.hermes/skills/agent-skills/`)

Ported ready-made skills (eval-tested upstream, ship Python scripts):

| Skill | What it does |
|-------|-------------|
| `advisor-orchestrator-worker` | Plan → delegate → verify → synthesize with a model team |
| `commit-archaeologist` | "Why does this code exist" from git history |
| `dependency-doctor` | Dependency manifest rot checks |
| `project-graveyard` | Autopsy dead side projects, pick one to resurrect |
| `scope-creep-detector` | Keep/split/justify for bloated diffs |
| `thinking-out-loud` | Echo-brief contract for voice rambles |
| `deep-research-patterns` | Multi-source → verify → cited report workflow |
| `llm-memory-patterns` | Persistent memory patterns for LLM apps |
| `token-optimization` | Reduce token usage / API cost |
| `voice-agent-patterns` | Voice RAG, TTS pipelines, live voice teams |

**Main profile ops skill (2026-08-21):** `hermes-cron-ops` (autonomous-ai-agents) — fixing/editing Hermes cron jobs across profiles: TIRITH `exfil_curl_url` scanner workaround (helper-script pattern), `HERMES_HOME` targeting for other profiles' cron stores, profile-local script paths, verify-by-trigger workflow. Created while repairing the investor daily briefing prompt.

## Per-profile distilled skills

| Profile | Skill | Source apps |
|---------|-------|-------------|
| architect | `system-architecture-review` | ai_system_architect_r1 |
| architect | `multi-agent-team-patterns` | agent_teams (16 templates) + trust-gating |
| backend | `rag-pipeline-patterns` | rag-as-a-service, hybrid search, chat-with-X |
| backend | `agent-framework-patterns` | OpenAI SDK + Google ADK crash courses |
| frontend | `generative-ui-patterns` | shadcn generator, dashboard canvas |
| frontend | `multimodal-design-feedback` | design critique + UI/UX feedback teams |
| engineer | `always-on-agent-patterns` | HN briefing, release radar, MCP router |
| engineer | `llm-finetuning-recipes` | Gemma 3 / Llama 3.2 LoRA with Unsloth |
| researcher | `deep-research-patterns` | core research workflow |
| researcher | `llm-memory-patterns` | research context persistence |
| researcher | `token-optimization` | keep research extract costs down |

**investor** (2026-08-19): standard fleet skill set + custom `finance/` skills — `investment-analysis`, `market-briefing`, `market-data-sources`, `playbook-trading` (discretionary play book workflow, added 2026-08-20), `revx-account`, `revx-auth`, `revx-market`, `revx-monitor`, `revx-strategy`, `revx-telegram`, `revx-trading` (Revolut X API workflows; custom, not distilled from awesome-llm-apps) — plus `agent-skills/` (`deep-research-patterns`, `llm-memory-patterns`, `token-optimization`).

**architect** (2026-08-20): added two custom homelab skills — `homelab-web-deploy` (devops; CI→GHCR→k3s rollout deploy/verify) and `headless-web-ui-verification` (software-development; headless browser/screenshot UI verification with vision_analyze).

## Related

- [[Researcher Agent]]
- [[Agent Overview]]
- Repo: `~/GitHub/awesome-llm-apps` (update source: `git -C ~/GitHub/awesome-llm-apps pull`)
