# Nous Subscription — Model Pricing Reference

> **Last updated:** 2026-08-16
> **Source:** [portal.nousresearch.com](https://portal.nousresearch.com/) and [pricepertoken.com](https://pricepertoken.com/pricing-page/provider/nousresearch)
> **Total models available:** 324 (via Nous API / OpenRouter routing)
> All prices are **per 1M tokens** (input / output) unless otherwise noted.

---

## Current Configuration

| Setting | Value |
|---------|-------|
| Active model | `z-ai/glm-5.2` |
| Provider | Nous Portal |
| Price | $0.25 in / $0.77 out per 1M |
| Fallback 0 | `openai/gpt-5.6-luna` |
| Fallback 1 | `lmstudio/qwen3.5-9b-mlx` (local) |

---

## Free Models ($0.00)

| Model | Notes |
|-------|-------|
| Meituan: LongCat 2.0 | General chat |
| Poolside: Laguna S 2.1 | Coding-focused |
| Poolside: Laguna XS 2.1 | Coding-focused, smaller |
| StepFun: Step 3.7 Flash | Fast, general |
| Tencent: Hy3 | General |
| Upstage: Solar Pro 4 | General |

---

## Ultra-Cheap (< $0.10 in / 1M tokens)

| Model | In | Out | Context | Best For |
|-------|----|----|---------|----------|
| inclusionAI: Ling-2.6-flash | $0.01 | $0.02 | — | Cheapest option, basic tasks |
| inclusionAI: Ling-3.0-flash | $0.02 | $0.05 | — | Ultra-cheap |
| OpenAI: gpt-oss-20b | $0.02 | $0.10 | — | Open-weight GPT |
| OpenAI: gpt-oss-120b | $0.02 | $0.14 | — | Larger open-weight GPT |
| DeepHermes 3 Mistral 24B | $0.02 | $0.10 | 33K | Reasoning, Nous's own |
| Mistral: Mistral Nemo | $0.02 | $0.02 | — | Cheapest output |
| Nex AGI: Nex-N2-Mini | $0.02 | $0.08 | — | Budget mini |
| Amazon: Nova Micro 1.0 | $0.03 | $0.11 | — | Fast, cheap |
| OpenAI: GPT-5 Nano | $0.04 | $0.32 | — | OpenAI budget |
| Meta: Llama 3.1 8B | $0.04 | $0.06 | 8K | Lightweight |
| IBM: Granite 4.1 8B | $0.04 | $0.08 | — | Enterprise lightweight |
| Qwen: Qwen3.7 Flash | $0.02 | $0.10 | — | Fast Qwen |
| Qwen: Qwen3.5-Flash | $0.05 | $0.21 | — | Good value |
| Z.ai: GLM 4.7 Flash | $0.05 | $0.32 | — | GLM budget |
| DeepSeek V4 Flash Latest | $0.05 | $0.10 | — | DeepSeek budget |
| Upstage: Solar Pro 4 | $0.02 | $0.10 | — | Also has free tier |
| ByteDance: Seed 1.6 Flash | $0.06 | $0.24 | — | Fast |
| Qwen: Qwen3 14B | $0.10 | $0.19 | — | Good small model |

---

## Budget ($0.10–$0.30 in / 1M tokens)

| Model | In | Out | Notes |
|-------|----|----|-------|
| **Z.ai: GLM 5.2** ⬅ *current* | $0.25 | $0.77 | Good balance |
| OpenAI: GPT-4o-mini | $0.12 | $0.48 | Reliable, fast |
| OpenAI: GPT-5.6 Luna | $0.10 | $0.60 | Newer, good value |
| OpenAI: GPT-5 Mini | $0.20 | $1.60 | Mid-range OpenAI |
| Anthropic: Claude 3 Haiku | $0.20 | $1.00 | Cheap Claude |
| Google: Gemini 2.5 Flash Lite | $0.08 | $0.32 | Very cheap Google |
| Google: Gemini 2.5 Flash | $0.24 | $2.00 | Popular mid-tier |
| Google: Gemini 3.7 Flash | $0.30 | $1.50 | Newer flash |
| Z.ai: GLM 4.5 Air | $0.10 | $0.68 | GLM budget |
| Z.ai: GLM 5.2 (batch) | $0.56 | $1.76 | Batch discount |
| Meta: Llama 4 Scout | $0.08 | $0.24 | Open-weight |
| Meta: Llama 4 Maverick | $0.16 | $0.64 | Larger |
| Meta: Llama 3.3 70B | $0.08 | $0.26 | Great value 70B |
| Mistral: Mistral Small 3.2 24B | $0.08 | $0.20 | Good value |
| Mistral: Mistral Small 4 | $0.12 | $0.48 | |
| Qwen: Qwen Plus | $0.21 | $0.62 | Solid all-rounder |
| Qwen: Qwen3 32B | $0.06 | $0.22 | Cheap 32B |
| Qwen: Qwen3 Coder 30B A3B | $0.06 | $0.22 | Coding-specific |
| ByteDance: Seed-2.0-Mini | $0.08 | $0.32 | |
| DeepSeek V3.1 | $0.20 | $0.76 | Strong value |
| DeepSeek V3.2 | $0.22 | $0.32 | Cheap output |
| MiniMax: MiniMax M2 | $0.20 | $0.82 | |
| MiniMax: MiniMax M2.5 | $0.18 | $0.72 | |
| Cohere: Command R | $0.12 | $0.48 | RAG-optimized |
| Amazon: Nova Lite 1.0 | $0.05 | $0.19 | |
| Amazon: Nova 2 Lite | $0.24 | $2.00 | |
| Arcee AI: Trinity Large Thinking | $0.18 | $0.68 | Reasoning |
| Xiaomi: MiMo-V2.5 | $0.11 | $0.22 | |

---

## Mid-Tier ($0.30–$1.00 in / 1M tokens)

| Model | In | Out | Notes |
|-------|----|----|-------|
| Z.ai: GLM 5.1 | $0.77 | $2.43 | Step up from current |
| Z.ai: GLM 5 | $0.48 | $1.54 | |
| Z.ai: GLM 4.6 | $0.44 | $1.76 | |
| Z.ai: GLM 4.7 | $0.32 | $1.40 | |
| Z.ai: GLM 5 Turbo | $0.96 | $3.20 | Faster GLM 5 |
| Anthropic: Claude Haiku Latest | $0.80 | $4.00 | Fast Claude |
| Anthropic: Claude Sonnet 5 (batch) | $0.80 | $4.00 | Batch Claude |
| DeepSeek: R1 0528 | $0.40 | $1.72 | Reasoning model |
| DeepSeek: R1 | $0.56 | $2.00 | Reasoning |
| DeepSeek: V4 Pro 0813 | $0.35 | $0.70 | Good value pro |
| DeepSeek: V4 Pro | $0.93 | $1.87 | |
| Google: Gemini 3 Flash Preview | $0.40 | $2.40 | |
| Google: Gemini 3.6 Flash | $0.60 | $3.00 | |
| MoonshotAI: Kimi K2.6 | $0.43 | $1.82 | |
| MoonshotAI: Kimi K2.7 Code | $0.57 | $2.80 | Coding-focused |
| Mistral: Mistral Medium 3 | $0.32 | $1.60 | |
| Mistral: Codestral 2508 | $0.24 | $0.72 | Coding |
| Qwen: Qwen3 Max | $0.62 | $3.12 | Top Qwen |
| Qwen: Qwen3 Coder Plus | $0.52 | $2.60 | Coding |
| Qwen: Qwen3.5 397B A17B | $0.31 | $1.87 | Large MoE |
| xAI: Grok 4.3 | $1.00 | $2.00 | |
| NVIDIA: Nemotron 3 Ultra | $0.48 | $2.88 | |

---

## Premium ($1.00–$3.00 in / 1M tokens)

| Model | In | Out | Notes |
|-------|----|----|-------|
| Anthropic: Claude Sonnet 4.5 | $2.40 | $12.00 | Top coding Claude |
| Anthropic: Claude Sonnet 4 | $2.40 | $12.00 | |
| OpenAI: GPT-5.2 | $1.40 | $11.20 | Strong all-rounder |
| OpenAI: GPT-5.1 | $1.00 | $8.00 | |
| OpenAI: GPT-5.4 | $2.00 | $12.00 | |
| OpenAI: GPT-5 | $1.00 | $8.00 | |
| Google: Gemini 2.5 Pro | $1.00 | $8.00 | |
| Google: Gemini 3.1 Pro Preview | $1.60 | $9.60 | |
| Google: Gemini 3.5 Flash | $1.20 | $7.20 | |
| xAI: Grok 4.5 | $1.60 | $4.80 | |
| xAI: Grok 4.6 | $1.60 | $4.80 | Latest Grok |
| MoonshotAI: Kimi K3 | $2.40 | $12.00 | |
| MoonshotAI: Kimi Latest | $2.24 | $11.20 | |
| Mistral Large | $1.60 | $4.80 | |
| Mistral: Mistral Medium 3.5 | $1.20 | $6.00 | |
| Cohere: Command R+ | $2.00 | $8.00 | RAG-focused |
| ByteDance: Seed 2.1 Turbo | $0.40 | $2.00 | |
| ByteDance: Seed-2.0-Code | $0.40 | $2.40 | Coding |

---

## Ultra-Premium ($3.00+ in / 1M tokens)

| Model | In | Out | Notes |
|-------|----|----|-------|
| Anthropic: Claude Opus Latest | $4.00 | $20.00 | Top-tier Claude |
| Anthropic: Claude Opus 4.5 | $4.00 | $20.00 | |
| Anthropic: Claude Fable Latest | $8.00 | $40.00 | Absolute premium |
| OpenAI: GPT-5.5 | $4.00 | $24.00 | Latest GPT |
| OpenAI: GPT Latest | $4.00 | $24.00 | |
| OpenAI: o3 | $1.60 | $6.40 | Reasoning |
| OpenAI: o3 Pro | $16.00 | $64.00 | Max reasoning |
| OpenAI: GPT-5 Pro | $12.00 | $96.00 | Max GPT |
| Sakana: Fugu Ultra | $4.00 | $24.00 | |

---

## Quick Picks by Use Case

| Use Case | Recommended Model | Price (in/out) | Why |
|----------|-------------------|-----------------|-----|
| Best value overall | Z.ai: GLM 5.2 (current) | $0.25 / $0.77 | Excellent price-to-performance |
| Budget coding | Qwen: Qwen3 Coder 30B A3B | $0.06 / $0.22 | Dirt cheap, coding-tuned |
| Budget general | Meta: Llama 3.3 70B | $0.08 / $0.26 | 70B quality at mini prices |
| Best value reasoning | DeepSeek: R1 0528 | $0.40 / $1.72 | Strong reasoning, reasonable cost |
| Premium coding | Anthropic: Claude Sonnet 4.5 | $2.40 / $12.00 | Top coding benchmarks |
| Premium all-rounder | OpenAI: GPT-5.2 | $1.40 / $11.20 | Excellent agentic performance |
| Best Google | Google: Gemini 2.5 Pro | $1.00 / $8.00 | Long context, multimodal |
| Cheapest usable | Mistral: Mistral Nemo | $0.02 / $0.02 | Almost free, basic tasks |

---

## How to Switch Models

```bash
# Set the default model
hermes config set model.default <provider/model-name>

# Or interactively select
hermes model
```

The model string format is `provider/model-name` (e.g. `z-ai/glm-5.2`, `openai/gpt-5.2`, `anthropic/claude-4.5-sonnet-20250929`).

---

## Tool Pricing (Non-Model)

| Tool | Unit | Price |
|------|------|-------|
| Browser Use | per minute | $0.0011 |
| Browser Use bandwidth | per GB | $4.20 |
| Firecrawl | per credit | $0.0005 |
| FAL image gen (Flux 2 Klein 9B) | per billable unit | $0.0116 |
| FAL image gen (Flux 2 Pro) | per billable unit | $0.0315 |
| FAL video gen (FLUX 3) | per billable unit | $0.0893 |
| Modal compute | per CPU-hour | $0.0495 |
| Modal memory | per GiB-hour | $0.0084 |
| Whisper STT | per minute of audio | $0.0063 |
| OpenAI TTS | per 1M output tokens | $12.60 |
