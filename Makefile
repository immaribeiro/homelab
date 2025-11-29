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
