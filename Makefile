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
