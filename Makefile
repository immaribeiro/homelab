## Add-ons automation
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

cf-secret:
	@if [ -z "$(CLOUDFLARE_API_TOKEN)" ]; then echo "Error: set CLOUDFLARE_API_TOKEN env var"; exit 1; fi
	kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -
	kubectl -n cert-manager delete secret cloudflare-api-token-secret --ignore-not-found
	kubectl -n cert-manager create secret generic cloudflare-api-token-secret --from-literal=api-token=$(CLOUDFLARE_API_TOKEN)

issuers:
	@echo "Applying ClusterIssuers..."
	kubectl apply -f k8s/cert-manager/clusterissuers.yaml
	kubectl get clusterissuers

wildcard:
	@echo "Applying wildcard certificate for *.lab.immas.org..."
	kubectl apply -f k8s/cert-manager/certificate-wildcard.yaml
	kubectl -n cert-manager get secret wildcard-lab-immas-org-tls || true

deploy-home:
	@echo "Applying home app and ingress..."
	kubectl apply -f k8s/manifests/home.yml
	kubectl apply -f k8s/manifests/home-ingress.yaml
	kubectl get ingress

## Kubeconfig convenience
.PHONY: kubeconfig

kubeconfig:
	@echo "Fetching and patching kubeconfig from control plane..."
	bash lima/scripts/fetch-kubeconfig.sh k3s-control-1 192.168.105.2

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
	@echo "Cloudflare Tunnel applied. Ensure DNS: hello.lab.immas.org CNAME -> $(TUNNEL_ID).cfargotunnel.com"

.PHONY: ingress-nginx
ingress-nginx:
	@echo "Installing ingress-nginx controller (LoadBalancer)..."
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.1/deploy/static/provider/cloud/deploy.yaml
	kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=180s || true
	kubectl -n ingress-nginx get svc -o wide

.PHONY: addons-status
addons-status: addons status-all
	@echo "Add-ons installed and cluster status displayed."


SHELL := /bin/zsh

# Configurable defaults
CONTROL ?= 1
WORKERS ?= 2
VM_NAMES ?= k3s-control-1 k3s-worker-1 k3s-worker-2

.PHONY: setup create bootstrap inventory install status teardown reset clean

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
	@echo "[inventory] Generating ansible/inventory-static-ip.yml"
	@bash lima/scripts/generate-inventory-from-limactl.sh > ansible/inventory-static-ip.yml
	@echo "[inventory] Done: ansible/inventory-static-ip.yml"

install:
	@echo "[install] Running K3s install via Ansible"
	@cd ansible && ansible-playbook -i inventory-static-ip.yml playbooks/k3s-install.yml

status:
	@echo "[status] Cluster nodes and pods"
	@bash lima/scripts/cluster-status.sh

teardown:
	@echo "[teardown] Full teardown (UNINSTALL_K3S=$(UNINSTALL_K3S), CLEAN_KUBECONFIG=$(CLEAN_KUBECONFIG), DEEP_CLEAN=$(DEEP_CLEAN))"
	@UNINSTALL_K3S=$(UNINSTALL_K3S) CLEAN_KUBECONFIG=$(CLEAN_KUBECONFIG) DEEP_CLEAN=$(DEEP_CLEAN) bash lima/scripts/teardown.sh

reset: teardown create bootstrap inventory install status

clean:
	@echo "[clean] Removing generated inventory"
	@rm -f ansible/inventory-static-ip.yml
