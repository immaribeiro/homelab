---
created: 2026-08-18
updated: 2026-08-18
model: deepseek/deepseek-v4-flash
provider: nous
---

# Researcher Agent

## Role

Deep research agent: web research, market/competitor intelligence, academic papers, and cited reports. Picks up research requests that deserve a multi-source, cited deliverable instead of a quick answer.

## Configuration

| Field | Value |
|-------|-------|
| **Profile** | researcher |
| **Config** | `~/GitHub/homelab/hermes/profiles/researcher/config.yaml` |
| **Model** | `deepseek/deepseek-v4-flash` via Nous |
| **Cost** | $0.05 in / $0.10 out per 1M (ultra-cheap) |
| **Fallback** | GLM 5.2 via Nous → LMStudio qwen3.5-9b-mlx |
| **Telegram** | 🔬 Research topic (thread 431) |
| **Reasoning** | medium |
| **Max turns** | 120 |
| **Terminal cwd** | `/Users/imma/GitHub` |

## Why DeepSeek V4 Flash?

Ultra-cheap ($0.05/$0.10 per 1M) — research workloads are token-hungry (long web extracts, many sources), so per-token cost dominates. GLM 5.2 fallback covers reasoning-heavy synthesis; local qwen3.5 is the free last resort. No TTS/image/video tools — research is text out.

## Skills

Core: `deep-research-patterns` (multi-source gathering → analysis → synthesis → cited output), `llm-memory-patterns`, `token-optimization` (keep extract/cost under control). Plus standard research category: arxiv, grounded-citations, competitor-news-monitor, blogwatcher, blocked-page-recovery, research-paper-writing.

## Workflow

1. Frame the question + scope + confidence bar (from `deep-research-patterns`)
2. Multi-source gather: web, papers, primary sources
3. Verify + flag contradictions
4. Structured cited report with confidence labels and open questions

## Telegram

🔬 Research topic — thread 431, wired in `config.yaml` `profile_routes` as `tg-researcher`. Group `-1004449482428`.

## Related

- [[Agent Overview]]
- [[Main Agent]] — routes research requests here
