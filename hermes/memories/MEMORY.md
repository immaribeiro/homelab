_Created: 2026-03-30_
§
Key Facts: First session started 2026-03-30
§
Configuration Hierarchy: hermes.json defines provider/model definitions, config.yaml controls runtime settings. Changes to hermes.json alone don't take effect - both files must be updated for new providers/models to work. API keys belong in .env, settings in config.yaml.
§
Ongoing Projects: Mac Mini (imma-mini) is the always-on Hermes hub — dashboard on :9119 (launchd: ai.hermes.dashboard), gateway running (launchd: ai.hermes.gateway), Tailscale: 100.101.63.91. Homelab repo at /Users/imma/GitHub/homelab. Multi-agent profiles configured: architect (DeepSeek R1), backend (Qwen3 Coder), frontend (LMStudio local). All Hermes configs synced to ~/GitHub/homelab/hermes/ via symlinks. Telegram routing docs at hermes/docs/telegram-routing.md.
§
Homelab: Mac Mini (imma-mini, 100.101.63.91) M4 24GB. Hermes hub, gateway multiplex_profiles enabled. 3 agent profiles: architect (DeepSeek R1 via Nous), backend (Qwen3 Coder 30B via Nous), frontend (Qwen 3.5 9B via LMStudio local). LMStudio models: qwen3.5-9b-mlx, google/gemma-4-e4b. Frontend uses qwen locally, backend falls back to gemma to avoid LMStudio model-slot conflicts. Telegram bot: @ImmaHermesBot. All Hermes config files symlinked from ~/.hermes/ to ~/GitHub/homelab/hermes/ for git sync.
§
User works across multiple machines (Mac Mini as hub, Mac Air as client). Wants same Hermes sessions/memory/skills from any machine. NordVPN on Mac Mini conflicts with Tailscale — use LAN IP fallback or router-level VPN.
§
Homelab repo at /Users/imma/GitHub/homelab contains infrastructure configs. Nous model pricing reference saved there as nous-model-pricing.md.