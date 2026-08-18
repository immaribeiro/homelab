---
created: 2026-08-16
updated: 2026-08-18
---

# 💰 Cost Tracking

Model costs and daily estimates for each agent. Prices per 1M tokens (input / output), from `nous-model-pricing.md` (repo root).

## Active Models

| Agent | Model | In | Out | Notes |
|-------|-------|----|-----|-------|
| Main | `gpt-5.6-luna` via openai-codex (ChatGPT Go) | $0.00 | $0.00 | Covered by ChatGPT subscription — no per-token charge |
| Architect | `deepseek/deepseek-v4-pro-0813` via Nous | $0.35 | $0.70 | Deep reasoning |
| Backend | `deepseek/deepseek-v4-flash` via Nous | $0.05 | $0.10 | Ultra-cheap |
| Frontend | `qwen3.5-9b-mlx` (LMStudio local) | $0.00 | $0.00 | FREE |
| Engineer | `deepseek/deepseek-v4-flash` via Nous | $0.05 | $0.10 | Ultra-cheap |
| Researcher | `deepseek/deepseek-v4-flash` via Nous | $0.05 | $0.10 | Ultra-cheap |

## Fallback Models

| Model | In | Out | Used by |
|-------|----|-----|---------|
| `deepseek/deepseek-v4-flash` via Nous | $0.05 | $0.10 | Main fallback 0, Frontend fallback 0 |
| `z-ai/glm-5.2` via Nous | $0.25 | $0.77 | Architect fallback 0, Backend fallback 1, Frontend fallback 1, Engineer fallback 0 |
| `openai/gpt-5.6-luna` via Nous | $0.10 | $0.60 | Delegation (all profiles) |
| `lmstudio/qwen3.5-9b-mlx` (local) | $0.00 | $0.00 | Main fallback 1, Architect fallback 1, Researcher fallback 1 |
| `lmstudio/google/gemma-4-e4b` (local) | $0.00 | $0.00 | Backend fallback 0, Engineer fallback 1 |

## Daily Cost Estimate

Rough estimates — actual cost depends on usage and how often fallbacks fire.

| Agent | Est. tokens/day | Cost/day |
|-------|-----------------|----------|
| main | ~50K | ~$0.00 (subscription; Nous fallback only) |
| architect | ~30K | ~$0.03 |
| backend | ~100K | ~$0.02 |
| frontend | ~100K (local) | $0.00 |
| engineer | ~50K | ~$0.01 |
| researcher | ~30K | ~$0.01 |
| **Total** | **~360K** | **~$0.07/day** |

**Monthly estimate:** ~$2.10 (if usage is consistent)

**Comparison:** if all 6 agents ran on GLM 5.2 exclusively: ~$0.41/day ≈ ~$12/month
**Savings:** ~80% reduction by using ChatGPT subscription + cheap/local models.

## Full Price Reference

→ [nous-model-pricing.md](../../../nous-model-pricing.md) in the homelab repo root

## Related

- [[Agent Overview]]
