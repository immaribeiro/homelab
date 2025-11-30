#!/bin/zsh
set -euo pipefail

print() { echo "[teardown] $1"; }

# 1) Optional: uninstall K3s from existing VMs
if [[ "${UNINSTALL_K3S:-1}" == "1" ]]; then
  if [[ -d "${PWD}/../ansible" ]]; then
    print "Uninstalling K3s via Ansible (if inventory available)"
    if [[ -f "${PWD}/../ansible/inventory.yml" ]]; then
      (cd ../ansible && ansible-playbook playbooks/k3s-reset.yml || true)
    elif [[ -f "${PWD}/../ansible/inventory.yml" ]]; then
      (cd ../ansible && ansible-playbook -i inventory.yml playbooks/k3s-reset.yml || true)
    else
      print "No inventory found; skipping K3s uninstall"
    fi
  fi
fi

# 2) Destroy Lima VMs
print "Destroying Lima VMs (k3s-control-*, k3s-worker-*)"
bash "$(dirname "$0")/destroy-vms.sh" || true

# 3) Clean kubeconfig (optional)
if [[ "${CLEAN_KUBECONFIG:-1}" == "1" ]]; then
  print "Cleaning ~/.kube/config"
  rm -f ~/.kube/config || true
fi

# 4) Clean known_hosts entries for forwarded ports (best-effort)
print "Cleaning known_hosts entries for current forwarded ports"
limactl list --json | jq -r '.[].sshLocalPort' | while read -r port; do
  [[ -n "$port" ]] && ssh-keygen -R "[127.0.0.1]:$port" >/dev/null 2>&1 || true
done

# 5) Optional deep clean of Lima state
if [[ "${DEEP_CLEAN:-0}" == "1" ]]; then
  print "Deep cleaning ~/.lima k3s-* instances"
  rm -rf ~/.lima/k3s-* || true
  print "(Optional) remove Lima download cache: ~/Library/Caches/lima/download"
fi

print "Teardown complete"
