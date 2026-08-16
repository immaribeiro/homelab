---
created: 2026-08-16
updated: 2026-08-16
---

# 💰 Cost Tracking

Model costs and daily estimates for each agent.

## Model Pricing (per 1M tokens)

### Active Models

| Agent | Model | Input | Output | Context |
|-------|-------|-------|--------|---------|
| Main | $0.05 in / $0.10 out | $0.25 | $0.77 | — |
| Architect | deepseek/r1-0528 | $0.40 | $1.72 | — |
| Backend | deepseek/deepseek-v4-flash | $0.06 | $0.22 | — |
| Frontend | qwen3.5-9b-mlx (local) | $0.00 | $0.00 | — |

### Fallback Models

| Model | Input | Output | Used by |
|-------|-------|--------|---------|
| openai/gpt-5.6-luna | $0.10 | $0.60 | Main fallback 0, delegation |
| $0.05 in / $0.10 out | $0.25 | $0.77 | Architect fallback 0, Backend fallback 1, Frontend fallback 1 |
| lmstudio/qwen3.5-9b-mlx | $0.00 | $0.00 | Main fallback 1, Architect fallback 1 |
| lmstudio/google/gemma-4-e4b | $0.00 | $0.00 | Backend fallback 0 |
| deepseek/deepseek-v4-flash | $0.06 | $0.22 | Frontend fallback 0 |

## Daily Cost Estimate

| Agent | Est. tokens/day | Cost/day |
|-------|-----------------|----------|
| main | ~50K in / 50K out | $0.05 |
| architect | ~30K in / 30K out | $0.06 |
| backend | ~100K in / 100K out | $0.03 |
| frontend | ~100K (local) | $0.00 |
| engineer | ~50K in / 50K out | $0.01 |
| **Total** | **~330K** | **~$0.15/day** |

**Monthly estimate:** ~$4.50 (if usage is consistent)

**Comparison:** If all 5 agents used GLM 5.2 exclusively: ~$0.65/day = ~$19.50/month
**Savings:** ~77% reduction by using cheap/local models where appropriate.

## Full Price Reference

→ [nous-model-pricing.md](../../../nous-model-pricing.md) in the homelab repo root

## Related

- [[Agent Overview]]
