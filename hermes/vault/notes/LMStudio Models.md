---
created: 2026-08-16
updated: 2026-08-19
---

# 🧠 LMStudio Models

Local models running on LMStudio (Mac Mini M4, 24GB RAM).

## Available Models

| Model ID | Type | Used By | Notes |
|----------|------|---------|-------|
| `qwen3.5-9b-mlx` | LLM (9B) | Frontend/Architect (offline fallback), Main/Researcher/Investor (fallback) | General + coding, MLX-optimized |
| `google/gemma-4-e4b` | LLM (4B) | Backend + Engineer (fallback) | Different model than frontend to avoid slot conflicts |
| `text-embedding-nomic-embed-text-v1.5` | Embedding | — | For future RAC/vector search |

## LMStudio Endpoint

- **Local:** `http://localhost:1234/v1`
- **LAN:** `http://192.168.8.161:1234/v1`
- **API key:** `sk-dummy` (LMStudio doesn't require real auth)

## Model-Slot Strategy

LMStudio can serve one model at a time (unless multi-model mode is enabled). To avoid conflicts:

- **Frontend** uses `qwen3.5-9b-mlx` as **offline fallback** (primary is `deepseek/deepseek-v4-flash` via Nous since 2026-08-18)
- **Backend** falls back to `google/gemma-4-e4b` (different model)
- This way, if both agents go local simultaneously, they use different models

If you enable LMStudio multi-model mode (loads multiple models simultaneously), this workaround is no longer needed — but watch RAM usage (24GB total, each model uses 4-10GB).

## Performance

| Model | Response time | Quality |
|-------|---------------|---------|
| qwen3.5-9b-mlx | ~30s | Good for simple tasks, struggles with complex logic |
| google/gemma-4-e4b | ~15s | Lighter, faster, less capable |

When the local model struggles, the fallback chain automatically switches to cloud models (deepseek-v4-flash via Nous, then GLM 5.2).

## Related

- [[Agent Overview]]
- [[Cost Tracking]]
