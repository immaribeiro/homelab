_Created: 2026-03-30_
§
Key Facts: First session started 2026-03-30
§
Configuration Hierarchy: hermes.json defines provider/model definitions, config.yaml controls runtime settings. Changes to hermes.json alone don't take effect - both files must be updated for new providers/models to work. API keys belong in .env, settings in config.yaml.
§
Ongoing Projects: Mac Mini (imma-mini) is the always-on Hermes hub — dashboard on :9119 (launchd: ai.hermes.dashboard), gateway running (launchd: ai.hermes.gateway), Tailscale: 100.101.63.91. Clients connect via Desktop → Connections → Remote gateway. Tailnet: imma-mini, gl-mt6000 router (100.107.9.6), iphone171, macbook-air. Homelab repo at /Users/imma/GitHub/homelab has nous-model-pricing.md.
§
Homelab: Mac Mini (imma-mini, 100.101.63.91) is the always-on Hermes hub. Dashboard: launchd ai.hermes.dashboard on 0.0.0.0:9119, basic auth (user: imma). Gateway: launchd ai.hermes.gateway. Both survive reboots. Tailscale app installed (not brew). Terminal cwd: /Users/imma. Connect remotely via Desktop → Connections → Remote gateway → Session token → http://imma-mini:9119. NordVPN on Mac Mini breaks Tailscale (no split tunneling on macOS) — use LAN IP (192.168.8.161:9119) as fallback when VPN is active, or move VPN to router.
§
User works across multiple machines (Mac Mini as hub, Mac Air as client). Wants same Hermes sessions/memory/skills from any machine. NordVPN on Mac Mini conflicts with Tailscale — use LAN IP fallback or router-level VPN.
§
Homelab repo at /Users/imma/GitHub/homelab contains infrastructure configs. Nous model pricing reference saved there as nous-model-pricing.md.