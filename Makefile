## Add-ons automation
# Load .env if it exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

.PHONY: addons metallb certmgr cf-secret issuers wildcard deploy-home

addons: metallb certmgr cf-secret issuers wildcard
	@echo "Add-ons installed and configured. Try: make deploy-home"

metallb:
	@echo "Installing MetalLB..."
	kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml
	kubectl -n metallb-system rollout status deploy/controller --timeout=120s || true
	kubectl apply -f k8s/metallb/metallb-config.yaml

certmgr:
	@echo "Installing cert-manager..."
	kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml
	kubectl -n cert-manager rollout status deploy/cert-manager --timeout=180s || true
	kubectl -n cert-manager rollout status deploy/cert-manager-webhook --timeout=180s || true
	kubectl -n cert-manager rollout status deploy/cert-manager-cainjector --timeout=180s || true

cf-secret:
	@if [ -z "$(CLOUDFLARE_ZONE_API_TOKEN)" ]; then echo "Error: set CLOUDFLARE_ZONE_API_TOKEN in .env"; exit 1; fi
	kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -
	kubectl -n cert-manager delete secret cloudflare-api-token-secret --ignore-not-found
	kubectl -n cert-manager create secret generic cloudflare-api-token-secret --from-literal=api-token=$(CLOUDFLARE_ZONE_API_TOKEN)

issuers:
	@echo "Applying ClusterIssuers..."
	kubectl apply -f k8s/cert-manager/clusterissuers.yaml
	kubectl get clusterissuers

wildcard:
	@echo "Applying wildcard certificate for *.immas.org..."
	kubectl apply -f k8s/cert-manager/certificate-wildcard.yaml
	kubectl -n cert-manager get secret wildcard-immas-org-tls || true

deploy-home:
	@echo "Applying home app..."
	kubectl apply -f k8s/manifests/home.yml
	kubectl -n default get pods,svc

deploy-vault:
	@echo "[deploy-vault] Deploying Vaultwarden..."
	kubectl apply -f k8s/manifests/vaultwarden.yml
	kubectl -n vaultwarden rollout status deploy/vaultwarden --timeout=120s || true
	@echo "[deploy-vault] Updating Cloudflare Tunnel..."
	kubectl apply -f k8s/cloudflared/tunnel.yaml
	kubectl -n cloudflared rollout restart deploy/cloudflared
	@echo ""
	@echo "✅ Vaultwarden deployed!"
	@echo ""
	@echo "Access at: https://vault.immas.org"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Visit https://vault.immas.org and create your account"
	@echo "  2. Install browser extension: https://bitwarden.com/download/"
	@echo "  3. In extension, set Server URL to: https://vault.immas.org"
	@echo "  4. After creating your account, disable signups:"
	@echo "     kubectl -n vaultwarden set env deploy/vaultwarden SIGNUPS_ALLOWED=false"
	@echo ""
	@echo "To sync with Apple Passwords:"
	@echo "  - Export from Vaultwarden (Settings → Export Vault → .csv)"
	@echo "  - Import to iCloud Keychain via System Settings → Passwords"

.PHONY: tunnel-route-vault-dns
tunnel-route-vault-dns:
	@if [ -z "$(TUNNEL_ID)" ] && [ -z "$(TUNNEL_NAME)" ]; then echo "Error: set TUNNEL_ID or TUNNEL_NAME in .env"; exit 1; fi
	@echo "[tunnel-route-vault-dns] Ensuring origin cert secret exists (requires local ~/.cloudflared/cert.pem)"
	@if [ ! -f "$(HOME)/.cloudflared/cert.pem" ]; then echo "Error: origin cert not found at $(HOME)/.cloudflared/cert.pem. Run: cloudflared login"; exit 1; fi
	kubectl create namespace cloudflared --dry-run=client -o yaml | kubectl apply -f -
	kubectl -n cloudflared delete secret cloudflared-origin-cert --ignore-not-found
	kubectl -n cloudflared create secret generic cloudflared-origin-cert --from-file=cert.pem=$(HOME)/.cloudflared/cert.pem
	@echo "[tunnel-route-vault-dns] Setting params ConfigMap (TUNNEL_REF + HOSTNAME)"
	TREF=$$(if [ -n "$(TUNNEL_NAME)" ]; then echo "$(TUNNEL_NAME)"; else echo "$(TUNNEL_ID)"; fi); \
	kubectl -n cloudflared create configmap cloudflared-dns-route-params \
	  --from-literal=TUNNEL_REF="$$TREF" \
	  --from-literal=HOSTNAME="vault.immas.org" \
	  --dry-run=client -o yaml | kubectl apply -f -
	@echo "[tunnel-route-vault-dns] Applying DNS route Job"
	kubectl apply -f k8s/cloudflared/dns-route-job.yaml
	@echo "[tunnel-route-vault-dns] Waiting for Job to complete..."
	kubectl -n cloudflared wait --for=condition=complete --timeout=90s job/cloudflared-dns-route || true
	@echo "[tunnel-route-vault-dns] Logs:"
	kubectl -n cloudflared logs job/cloudflared-dns-route --tail=100 || true
	@echo "[tunnel-route-vault-dns] Done. Verify DNS: dig +short vault.immas.org"

.PHONY: tunnel-route
# Usage: make tunnel-route HOST=<hostname>
tunnel-route:
	@if [ -z "$(HOST)" ]; then echo "Usage: make tunnel-route HOST=<hostname>"; exit 1; fi
	@if [ -z "$(TUNNEL_ID)" ] && [ -z "$(TUNNEL_NAME)" ]; then echo "Error: set TUNNEL_ID or TUNNEL_NAME in .env"; exit 1; fi
	@if [ ! -f "$(HOME)/.cloudflared/cert.pem" ]; then echo "Error: origin cert not found at $(HOME)/.cloudflared/cert.pem. Run: cloudflared login"; exit 1; fi
	kubectl create namespace cloudflared --dry-run=client -o yaml | kubectl apply -f -
	kubectl -n cloudflared delete secret cloudflared-origin-cert --ignore-not-found
	kubectl -n cloudflared create secret generic cloudflared-origin-cert --from-file=cert.pem=$(HOME)/.cloudflared/cert.pem
	TREF=$$(if [ -n "$(TUNNEL_NAME)" ]; then echo "$(TUNNEL_NAME)"; else echo "$(TUNNEL_ID)"; fi); \
	kubectl -n cloudflared create configmap cloudflared-dns-route-params \
	  --from-literal=TUNNEL_REF="$$TREF" \
	  --from-literal=HOSTNAME="$(HOST)" \
	  --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f k8s/cloudflared/dns-route-job.yaml
	kubectl -n cloudflared wait --for=condition=complete --timeout=90s job/cloudflared-dns-route || true
	kubectl -n cloudflared logs job/cloudflared-dns-route --tail=200 || true
	@echo "[tunnel-route] Done. Verify: dig +short $(HOST)"

.PHONY: verify-host
# Usage: make verify-host HOST=<hostname>
verify-host:
	@if [ -z "$(HOST)" ]; then echo "Usage: make verify-host HOST=<hostname>"; exit 1; fi
	@echo "[verify-host] DNS via system resolver:"
	dig +short $(HOST) || true
	@echo "[verify-host] DNS via Cloudflare resolver:"
	dig @1.1.1.1 +short $(HOST) || true
	@echo "[verify-host] HTTP response (may be proxied):"
	curl -I https://$(HOST) || true

.PHONY: argocd
argocd:
	@echo "[argocd] Installing ArgoCD"
	kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	@echo "[argocd] Configuring insecure mode for HTTP backend..."
	kubectl apply -f k8s/argocd/argocd-cmd-params-cm.yaml
	@echo "[argocd] Waiting for ArgoCD server to be ready..."
	kubectl -n argocd rollout status deploy/argocd-server --timeout=300s || true
	@echo "[argocd] Updating Cloudflare Tunnel for argocd.immas.org"
	kubectl apply -f k8s/cloudflared/tunnel.yaml
	kubectl -n cloudflared rollout restart deploy/cloudflared
	@echo ""
	@echo "✅ ArgoCD installed!"
	@echo ""
	@echo "Access: https://argocd.immas.org"
	@echo "Username: admin"
	@echo "Password: run 'make argocd-password'"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Route DNS: make tunnel-route HOST=argocd.immas.org"
	@echo "  2. Get password: make argocd-password"
	@echo "  3. Deploy apps: make argocd-apps"
	@echo "  4. Install CLI: brew install argocd"
	@echo "  5. Login: argocd login argocd.immas.org"

.PHONY: argocd-password
argocd-password:
	@echo "ArgoCD admin password:"
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo

.PHONY: argocd-apps
argocd-apps:
	@echo "[argocd-apps] Deploying app-of-apps..."
	kubectl apply -f k8s/argocd/app-of-apps.yaml
	@echo ""
	@echo "✅ App-of-apps deployed!"
	@echo ""
	@echo "ArgoCD will now manage all homelab applications:"
	@echo "  - homepage"
	@echo "  - home-assistant"
	@echo "  - plex"
	@echo "  - qbittorrent"
	@echo "  - vaultwarden"
	@echo "  - homelab-bot"
	@echo ""
	@echo "View apps: https://argocd.immas.org"
	@echo "Or: kubectl get applications -n argocd"

## Kubeconfig convenience
.PHONY: kubeconfig

kubeconfig:
	@echo "Fetching and patching kubeconfig from control plane..."
	@if [ -z "$(K3S_CONTROL_PLANE_IP)" ]; then echo "Error: set K3S_CONTROL_PLANE_IP in .env"; exit 1; fi
	bash lima/scripts/fetch-kubeconfig.sh k3s-control-1 $(K3S_CONTROL_PLANE_IP)

## Status helpers
.PHONY: status-all

status-all:
	@echo "Cluster info:"
	kubectl cluster-info
	@echo "\nNodes (wide):"
	kubectl get nodes -o wide
	@echo "\nAll pods:"
	kubectl get pods -A -o wide
	@echo "\nLoadBalancer services:"
	kubectl get svc -A | grep LoadBalancer || true
	@echo "\nTraefik service:"
	kubectl -n kube-system get svc -l app.kubernetes.io/name=traefik -o wide || true

.PHONY: traefik-lb
traefik-lb:
	@echo "Creating Traefik LoadBalancer Service..."
	kubectl apply -f k8s/manifests/traefik-lb.yaml
	kubectl -n kube-system get svc traefik-lb -o wide

.PHONY: tunnel
tunnel:
	@if [ -z "$(TUNNEL_ID)" ]; then echo "Error: set TUNNEL_ID env var"; exit 1; fi
	@if [ -z "$(TUNNEL_CRED_FILE)" ]; then echo "Error: set TUNNEL_CRED_FILE env var (path to <TUNNEL_ID>.json)"; exit 1; fi
	@if [ ! -f "$(TUNNEL_CRED_FILE)" ]; then echo "Error: credential file '$(TUNNEL_CRED_FILE)' not found"; exit 1; fi
	@echo "Creating/Refreshing cloudflared credentials secret from $(TUNNEL_CRED_FILE)..."
	kubectl create namespace cloudflared --dry-run=client -o yaml | kubectl apply -f -
	kubectl -n cloudflared delete secret cloudflared-credentials --ignore-not-found
	kubectl -n cloudflared create secret generic cloudflared-credentials --from-file=tunnel.json=$(TUNNEL_CRED_FILE)
	@echo "Applying cloudflared deployment and config..."
	kubectl apply -f k8s/cloudflared/tunnel.yaml
	kubectl -n cloudflared get deploy,po
	@echo "Cloudflare Tunnel applied. Ensure DNS: hello.immas.org CNAME -> $(TUNNEL_ID).cfargotunnel.com"

.PHONY: ingress-nginx
ingress-nginx:
	@echo "Installing ingress-nginx controller (LoadBalancer)..."
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.1/deploy/static/provider/cloud/deploy.yaml
	kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=180s || true
	kubectl -n ingress-nginx get svc -o wide

.PHONY: addons-status
addons-status: addons status-all
	@echo "Add-ons installed and cluster status displayed."

.PHONY: tunnel-setup
tunnel-setup:
	@echo "[tunnel-setup] Creating or reusing Cloudflare Tunnel and updating .env"
	@chmod +x scripts/cloudflared-setup.sh
	@ENV_FILE=.env scripts/cloudflared-setup.sh homelab
	@echo "[tunnel-setup] Done. Verify TUNNEL_ID and TUNNEL_CRED_FILE in .env."

.PHONY: release
release:
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release VERSION=v0.x.y"; exit 1; fi
	@if git rev-parse "$(VERSION)" >/dev/null 2>&1; then echo "Tag $(VERSION) already exists"; exit 1; fi
	@echo "Tagging release $(VERSION)"
	@git tag -a $(VERSION) -m "Release $(VERSION)"
	@git push origin $(VERSION)
	@if command -v gh >/dev/null 2>&1; then \
	  echo "Creating GitHub release $(VERSION)"; \
	  gh release create $(VERSION) -t "$(VERSION) Homelab" -n "Automated release $(VERSION)\nSee DEPLOYMENT.md for deployment steps."; \
	else \
	  echo "gh CLI not installed; create release manually in the GitHub UI."; \
	fi

.PHONY: backup
backup:
	@OUT_DIR=backups/$(shell date +%Y%m%d-%H%M%S); \
	 echo "Creating backup in $$OUT_DIR"; \
	 mkdir -p $$OUT_DIR; \
	 echo "Backing up Home Assistant config..."; \
	 HA_POD=$$(kubectl -n home-assistant get pod -l app=home-assistant -o jsonpath='{.items[0].metadata.name}'); \
	 kubectl -n home-assistant cp $$HA_POD:/config $$OUT_DIR/home-assistant-config; \
	 echo "Backing up Plex config..."; \
	 PLEX_POD=$$(kubectl -n plex get pod -l app=plex -o jsonpath='{.items[0].metadata.name}'); \
	 kubectl -n plex cp $$PLEX_POD:/config $$OUT_DIR/plex-config; \
	 echo "Creating tarballs"; \
	 tar -czf $$OUT_DIR/home-assistant-config.tgz -C $$OUT_DIR home-assistant-config; \
	 tar -czf $$OUT_DIR/plex-config.tgz -C $$OUT_DIR plex-config; \
	 rm -rf $$OUT_DIR/home-assistant-config $$OUT_DIR/plex-config; \
	 echo "Backup complete: $$OUT_DIR"

.PHONY: metrics
metrics:
	@echo "[metrics] Installing kube-prometheus-stack with Helm"
	@if ! command -v helm >/dev/null 2>&1; then echo "Error: helm not installed"; exit 1; fi
	@kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
	@echo "[metrics] Adding prometheus-community Helm repo"
	@helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
	@helm repo update prometheus-community
	@echo "[metrics] Installing/Upgrading kube-prometheus-stack"
	@helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
	  --namespace monitoring \
	  --values k8s/monitoring/values.yaml \
	  --wait --timeout 10m
	@echo "[metrics] Deployment complete. Check: kubectl -n monitoring get pods"
	@echo "[metrics] Grafana available at https://grafana.immas.org"
	@echo "[metrics] Default credentials: admin / admin (change on first login)"

.PHONY: grafana-reset
grafana-reset:
	@if [ -z "$(PASSWORD)" ]; then echo "Usage: make grafana-reset PASSWORD=<newpassword>"; exit 1; fi
	@echo "[grafana-reset] Resetting Grafana admin password inside pod to '$(PASSWORD)'"
	@POD=$$(kubectl -n monitoring get pods -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}'); \
	 kubectl -n monitoring exec $$POD -- grafana-cli admin reset-admin-password $(PASSWORD) || { echo "grafana-cli failed"; exit 1; }; \
	 echo "[grafana-reset] Done. Update Helm values (adminPassword) if you want this persisted on clean re-deploy.";
	@echo "[grafana-reset] Current secret value (may differ until Helm upgrade):"; \
	 kubectl -n monitoring get secret kube-prometheus-stack-grafana -o jsonpath='{.data.admin-password}' | base64 -d || true; echo

.PHONY: grafana-secret-sync
grafana-secret-sync:
	@if [ -z "$(PASSWORD)" ]; then echo "Usage: make grafana-secret-sync PASSWORD=<password-to-sync>"; exit 1; fi
	@echo "[grafana-secret-sync] Patching kube-prometheus-stack-grafana secret with provided password"
	kubectl -n monitoring patch secret kube-prometheus-stack-grafana -p '{"data":{"admin-password":"'$(shell printf "%s" "$(PASSWORD)" | base64)'"}}'
	@echo "[grafana-secret-sync] Secret patched. Rolling out restart."
	kubectl -n monitoring rollout restart deploy/kube-prometheus-stack-grafana
	kubectl -n monitoring rollout status deploy/kube-prometheus-stack-grafana --timeout=120s || true
	@echo "[grafana-secret-sync] Completed. Try logging in with: admin / $(PASSWORD)"


.PHONY: qb-add
qb-add:
	@if [ -z "$(MAGNET)" ]; then echo "Usage: make qb-add MAGNET='magnet:...' [SAVEPATH=/downloads]"; exit 1; fi
	@echo "[qb-add] Submitting magnet to qBittorrent..."
	@QB_USER=$(QB_USER) QB_PASS=$(QB_PASS) QB_HOST=$(QB_HOST) \
	  scripts/qb-add.sh '$(MAGNET)' $(if $(SAVEPATH),--savepath $(SAVEPATH),)
	@echo "[qb-add] Done"

.PHONY: grafana-set-password
# Rotate the password via Helm (chart-managed). Source of truth: Helm release values.
grafana-set-password:
	@if [ -z "$(PASSWORD)" ]; then echo "Usage: make grafana-set-password PASSWORD=<newpassword>"; exit 1; fi
	@if ! command -v helm >/dev/null 2>&1; then echo "Error: helm not installed"; exit 1; fi
	@echo "[grafana-set-password] Upgrading kube-prometheus-stack with new Grafana admin password via Helm"
	helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
	  --namespace monitoring \
	  --values k8s/monitoring/values.yaml \
	  --set grafana.adminPassword=$(PASSWORD) \
	  --wait --timeout 10m
	@echo "[grafana-set-password] Complete. Login with: admin / $(PASSWORD)"


SHELL := /bin/zsh

# Configurable defaults
CONTROL ?= 1
WORKERS ?= 2
VM_NAMES ?= k3s-control-1 k3s-worker-1 k3s-worker-2

.PHONY: setup create bootstrap inventory install status teardown reset clean cluster-setup

cluster-setup: create bootstrap inventory install
	@echo "✅ Cluster setup complete! Run 'make kubeconfig' to fetch kubeconfig, then 'make addons'"

setup:
	@echo "[setup] Installing prerequisites and configuring services"
	@bash setup.sh

create:
	@echo "[create] Creating $(CONTROL) control and $(WORKERS) worker VMs"
	@bash lima/scripts/create-vms.sh $(CONTROL) $(WORKERS)

bootstrap:
	@echo "[bootstrap] Installing SSH keys and sudoers on: $(VM_NAMES)"
	@bash lima/scripts/bootstrap-ssh.sh $(VM_NAMES)

inventory:
	@echo "[inventory] Generating ansible/inventory.yml"
	@bash lima/scripts/generate-inventory-from-limactl.sh > ansible/inventory.yml
	@echo "[inventory] Done: ansible/inventory.yml"

install:
	@echo "[install] Running K3s install via Ansible"
	@cd ansible && ansible-playbook playbooks/k3s-install.yml

status:
	@echo "[status] Cluster nodes and pods"
	@bash lima/scripts/cluster-status.sh

teardown:
	@echo "[teardown] Full teardown (UNINSTALL_K3S=$(UNINSTALL_K3S), CLEAN_KUBECONFIG=$(CLEAN_KUBECONFIG), DEEP_CLEAN=$(DEEP_CLEAN))"
	@UNINSTALL_K3S=$(UNINSTALL_K3S) CLEAN_KUBECONFIG=$(CLEAN_KUBECONFIG) DEEP_CLEAN=$(DEEP_CLEAN) bash lima/scripts/teardown.sh

reset: teardown create bootstrap inventory install status

clean:
	@echo "[clean] Removing generated inventory"
	@rm -f ansible/inventory.yml

## Server Restart & Recovery
.PHONY: start-vms stop-vms restart-vms verify-cluster post-reboot

start-vms:
	@echo "[start-vms] Starting all K3s VMs..."
	@for vm in $(VM_NAMES); do \
		echo "Starting $$vm..."; \
		limactl start $$vm 2>/dev/null || echo "$$vm already running or failed"; \
	done
	@echo "[start-vms] Waiting for VMs to initialize (15s)..."
	@sleep 15
	@limactl list

stop-vms:
	@echo "[stop-vms] Stopping all K3s VMs gracefully..."
	@for vm in $(VM_NAMES); do \
		echo "Stopping $$vm..."; \
		limactl stop $$vm 2>/dev/null || echo "$$vm already stopped"; \
	done
	@limactl list

restart-vms: stop-vms
	@echo "[restart-vms] Waiting 5s before restart..."
	@sleep 5
	@$(MAKE) start-vms

verify-cluster:
	@echo "[verify-cluster] Checking cluster health..."
	@echo "\n=== Nodes ==="
	@kubectl get nodes -o wide || echo "⚠️  Cannot reach cluster. Run: make kubeconfig"
	@echo "\n=== System Pods ==="
	@kubectl get pods -n kube-system || true
	@echo "\n=== MetalLB ==="
	@kubectl get pods -n metallb-system || true
	@echo "\n=== cert-manager ==="
	@kubectl get pods -n cert-manager || true
	@echo "\n=== Cloudflare Tunnel ==="
	@kubectl get pods -n cloudflared || true
	@echo "\n=== LoadBalancer Services ==="
	@kubectl get svc -A | grep LoadBalancer || echo "No LoadBalancer services found"
	@echo "\n=== Certificates ==="
	@kubectl get certificates -A || true

post-reboot: start-vms
	@echo "[post-reboot] VMs started. Fetching kubeconfig..."
	@sleep 10
	@$(MAKE) kubeconfig || echo "⚠️  Kubeconfig fetch failed. VMs may still be initializing."
	@echo "[post-reboot] Waiting for K3s to stabilize (30s)..."
	@sleep 30
	@$(MAKE) verify-cluster
	@echo "\n✅ Post-reboot recovery complete!"
	@echo "\nIf services are not responding:"
	@echo "  1. Check tunnel: kubectl -n cloudflared logs deploy/cloudflared --tail=50"
	@echo "  2. Restart tunnel: kubectl -n cloudflared rollout restart deploy/cloudflared"
	@echo "  3. Verify DNS: dig +short home.immas.org"
	@echo "  4. Check app pods: kubectl get pods -A | grep -v Running"

.PHONY: deploy-bot
deploy-bot:
	@if [ -z "$(BOT_TOKEN)" ] || [ -z "$(CHAT_ID)" ] || [ -z "$(QB_USER)" ] || [ -z "$(QB_PASS)" ]; then \
	  echo "Usage: make deploy-bot BOT_TOKEN=... CHAT_ID=... QB_USER=... QB_PASS=... [QB_URL=http://qbittorrent.qbittorrent.svc.cluster.local:8080]"; exit 1; fi
	@echo "[deploy-bot] Ensuring namespace automations exists"
	@kubectl create namespace automations --dry-run=client -o yaml | kubectl apply -f -
	@echo "[deploy-bot] Creating/Updating Secret homelab-bot-secret"
	@kubectl -n automations delete secret homelab-bot-secret --ignore-not-found
	@kubectl -n automations create secret generic homelab-bot-secret \
	  --from-literal=BOT_TOKEN=$(BOT_TOKEN) \
	  --from-literal=QB_USER=$(QB_USER) \
	  --from-literal=QB_PASS=$(QB_PASS) \
	  --from-literal=CHAT_ID=$(CHAT_ID)
	@echo "[deploy-bot] Applying bot manifest"
	@# Inject the current Python bot into the ConfigMap for runtime
	@kubectl -n automations create configmap homelab-bot-config \
	  --from-literal=QB_URL="$(or $(QB_URL),http://qbittorrent.qbittorrent.svc.cluster.local:8080)" \
	  --from-literal=SAVE_PATH="/downloads" \
	  --from-literal=AUTO_TMM="false" \
	  --from-file=bot.py=scripts/homelab-bot.py \
	  --dry-run=client -o yaml | kubectl apply -f -
	@kubectl apply -f k8s/manifests/homelab-bot.yml
	@kubectl -n automations rollout status deploy/homelab-bot --timeout=120s || true
	@echo "[deploy-bot] Homelab bot deployed. Send a magnet or /start to your Telegram bot to test."

## LM Studio (Bare Metal Mac)
.PHONY: lm-status lm-test lm-deploy lm-install deploy-chat chat-logs chat-restart chat-status

lm-install:
	@echo "[lm-install] Installing LM Studio via Homebrew..."
	@brew install --cask lm-studio || echo "LM Studio already installed or brew not available"
	@echo "✓ Installation complete. Run 'open -a \"LM Studio\"' to launch."
	@echo "📖 See LMSTUDIO.md for setup guide"

lm-status:
	@echo "[lm-status] Checking LM Studio server status..."
	@curl -sf http://localhost:1234/v1/models > /dev/null && \
		echo "✓ LM Studio server is running on http://localhost:1234" || \
		echo "✗ LM Studio server not responding. Start it in the LM Studio app (Local Server tab)"

lm-test:
	@echo "[lm-test] Testing LM Studio API..."
	@echo "Available models:"
	@curl -sf http://localhost:1234/v1/models | jq -r '.data[]? | "  - \(.id)"' || \
		echo "✗ Cannot connect to LM Studio. Ensure server is running."
	@echo ""
	@echo "Testing chat completion..."
	@curl -sf http://localhost:1234/v1/chat/completions \
		-H "Content-Type: application/json" \
		-d '{"model":"local-model","messages":[{"role":"user","content":"Say hello in one word"}],"max_tokens":10}' \
		| jq -r '.choices[0].message.content' || echo "✗ Chat test failed"

lm-deploy:
	@echo "[lm-deploy] Creating Kubernetes resources for LM Studio access..."
	@if [ -z "$(MAC_IP)" ]; then \
		echo "Error: Set MAC_IP in .env (your Mac's local IP, e.g. 192.168.1.100)"; \
		exit 1; \
	fi
	@kubectl create namespace ai --dry-run=client -o yaml | kubectl apply -f -
	@kubectl apply -f k8s/manifests/lmstudio-external.yml
	@echo "✓ LM Studio external service created in 'ai' namespace"
	@echo "Cluster apps can access: http://lmstudio.ai.svc.cluster.local:1234"

deploy-chat:
	@echo "[deploy-chat] Deploying Open WebUI chat interface..."
	@echo "Prerequisite: LM Studio must be running (make lm-status)"
	@kubectl apply -f k8s/manifests/open-webui.yml
	@kubectl -n chat rollout status deploy/open-webui --timeout=120s || true
	@echo ""
	@echo "✓ Chat UI deployed!"
	@echo "📱 Access: https://llm.immas.org"
	@echo "👤 First user to sign up becomes admin"
	@echo ""
	@echo "Next: Route DNS with 'make tunnel-route HOST=llm.immas.org'"

chat-logs:
	@echo "[chat-logs] Showing Open WebUI logs..."
	@kubectl -n chat logs -l app=open-webui --tail=100 -f

chat-restart:
	@echo "[chat-restart] Restarting Open WebUI..."
	@kubectl -n chat rollout restart deploy/open-webui
	@kubectl -n chat rollout status deploy/open-webui --timeout=120s

chat-status:
	@echo "[chat-status] Open WebUI Status:"
	@kubectl -n chat get pods,svc,ingress
	@echo ""
	@echo "💬 Chat UI: https://llm.immas.org"
	@echo "🔗 LM Studio: http://lmstudio.ai.svc.cluster.local:1234"
