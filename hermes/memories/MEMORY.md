_Created: 2026-03-30_
§
Key Facts: First session started 2026-03-30
§
Configuration Hierarchy: hermes.json defines provider/model definitions, config.yaml controls runtime settings. Changes to hermes.json alone don't take effect - both files must be updated for new providers/models to work. API keys belong in .env, settings in config.yaml.
§
Homelab: Mac Mini (imma-mini, 192.168.8.161 LAN, 100.101.63.91 Tailscale) M4 24GB. Always-on Hermes hub: dashboard :9119 (launchd: ai.hermes.dashboard, auth basic+nous OAuth, client agent:cmsw4ufm7007nho0as0osc2zn), publicly at https://hermes.immas.org via Cloudflare tunnel (ingress in k8s/cloudflared/tunnel.yaml, origin http://192.168.8.161:9119). Gateway (launchd: ai.hermes.gateway).
§
User works across multiple machines (Mac Mini as hub, Mac Air as client). Wants same Hermes sessions/memory/skills from any machine. NordVPN on Mac Mini conflicts with Tailscale — use LAN IP fallback or router-level VPN.
§
Engineer role: user expects proactive execution — start VMs, fix configs, deploy apps, restart services without asking permission. Full autonomy on infra ops.
§
K3s Lima cluster: VMs need `lima:shared` network (`limactl edit --network lima:shared`) for inter-VM comms. Creates `lima0` iface with DHCP on 192.168.105.x. K3s must use `--flannel-iface lima0`. On restart with new config, CA certs + node-token change — workers need new token from control plane.