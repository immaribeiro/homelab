---
created: 2026-08-19
updated: 2026-08-20
model: deepseek/deepseek-v4-flash
provider: nous
---

# 📈 Investor Agent

## Role

Markets & portfolio specialist of the fleet: watches crypto + stocks, turns news into signals, monitors Imma's portfolio, and proposes disciplined, risk-first decisions. The agent main hands "check the markets / what should we do about X" to.

## Configuration

| Field | Value |
|-------|-------|
| **Profile** | investor |
| **Config** | `~/GitHub/homelab/hermes/profiles/investor/config.yaml` |
| **Model** | `deepseek/deepseek-v4-flash` via Nous |
| **Cost** | $0.05 in / $0.10 out per 1M (ultra-cheap) |
| **Fallback 0** | `z-ai/glm-5.2` via Nous |
| **Fallback 1** | `lmstudio/qwen3.5-9b-mlx` (local, free) |
| **Telegram** | 📈 Investor topic — thread `1016` (`tg-investor` route, live since gateway restart 2026-08-19) |
| **Reasoning** | medium |
| **Max turns** | 120 |
| **Terminal cwd** | `/Users/imma/GitHub` |
| **MCP** | `revolutx` — Revolut X API (`~/GitHub/revolut-x-api/mcp`, node) |

## Why DeepSeek V4 Flash?

Ultra-cheap ($0.05/$0.10 per 1M) — monitoring/briefing workloads run on cron and should stay near-zero cost. GLM 5.2 covers deeper analysis; local qwen3.5 is the free last resort. No TTS/image/video tools — output is briefings and journals.

## SOUL

Custom (2026-08-19): signals-not-hype (verify before recommend), data-backed with cited sources, risk discipline first (whitelisted assets BTC/ETH/core ETFs, capped orders), watchdog mindset for cron jobs, journal every decision. **Play book exception (2026-08-20):** the ~€55 discretionary pool on Revolut X trades with **full discretion — no per-trade consent** (hard rules: no leverage, no meme coins, max €25/trade, max 2 positions, −€10 max daily loss, stop if book < €27); everything else stays approval-gated.

## Skills

- `finance/`: `investment-analysis`, `market-briefing`, `market-data-sources`, `playbook-trading` (discretionary play book workflow, 2026-08-20), `revx-account`, `revx-auth`, `revx-market`, `revx-monitor`, `revx-strategy`, `revx-telegram`, `revx-trading` (Revolut X API workflows)
- `agent-skills/`: `deep-research-patterns`, `llm-memory-patterns`, `token-optimization`
- Standard fleet skill categories (apple, creative, github, productivity, research, …)

## Rails (Execution)

- **Crypto:** Revolut X official REST API via the `revolutx` MCP server (private key at `~/.hermes/env/revolut-x-private.pem` — secret, not synced; API key in `~/.config/revolut-x/config.json` — MCP reads config file, not env vars)
- **Stocks:** Trading 212 — account created 2026-08-19; API key + secret pending from Imma (Settings → API (Beta) → Generate; Basic auth `API_KEY:API_SECRET`; demo env `demo.trading212.com/api/v0`, live `live.trading212.com/api/v0`). IBKR / eToro still possible alternatives.
- **News:** Marketaux token set in investor `.env` (verified live 2026-08-19 — use `api_token=` param, not `token=`); RSS fallback (Coindesk/Cointelegraph/The Block)
- **Play book (2026-08-20):** full discretion on the ~€55 pool (EUR working capital + USDT reserve — **Revolut X has no USDT pairs**, so trades run EUR-quote: ETH-EUR / BTC-EUR / SOL-EUR). Post-only limits at support, report every trade in thread + play-book.md + decisions-journal.md. Never touch Imma's long-term BTC/ETH holdings.
- Everything **outside** the play book is gated by Imma's approval — the agent proposes, never surprises.

## Telegram

Wired 2026-08-19: **📈 Investor** topic, thread `1016` in the Hermes group → `tg-investor` route in main `config.yaml`. Daily 07:30 briefing + Sat review + price watchdogs deliver here. Gateway restart required after config change (agent cannot restart itself — guard).

## Related

- [[Agent Overview]]
- [[Cost Tracking]]
