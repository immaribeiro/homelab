_Created: 2026-08-16_
§
Role: IT System Engineer — homelab infrastructure, K3s cluster, Lima VMs, Cloudflare tunnels, deployments, troubleshooting.
Primary model: Qwen3 Coder 30B via Nous ($0.06/$0.22). Fallback: GLM 5.2 → local Gemma 4.
Uses different LMStudio model (gemma) than frontend (qwen) to avoid model-slot conflicts.
§
Cluster: 3 Lima VMs (k3s-control-1, k3s-worker-1, k3s-worker-2). K3s with MetalLB (192.168.105.50-99), NGINX ingress, cert-manager, Cloudflare Tunnel, ArgoCD GitOps. 12+ deployed apps.
§
Recovery: `make post-reboot` starts everything. Manual: `make start-vms`, `make kubeconfig`, `make verify-cluster`.
§
Owner: Imma (@i6m6m6a). Homelab repo at ~/GitHub/homelab. Terminal cwd: /Users/imma/GitHub/homelab.
§
macOS quirk (this Mac): ~/Documents files can be dataless iCloud stubs — stat -f %Sf shows 'dataless', reads fail EDEADLK. Diagnose with: find <dir> -type f -exec stat -f '%Sf' {} \; | grep -c dataless. Aug-2026: iCloud Drive zone detached (brctl: Client zone not found; FPCK: disk<->FSSnapshot failed 248/42667); fix needs sudo fileproviderctl repair, Desktop&Documents toggle, or icloud.com download.