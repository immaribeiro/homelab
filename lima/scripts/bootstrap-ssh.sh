#!/bin/zsh
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <vm-name> [<vm-name> ...]"
  echo "Example: $0 k3s-control-1 k3s-worker-1 k3s-worker-2"
  exit 1
fi

PUBKEY_PATH=${PUBKEY_PATH:-$HOME/.ssh/id_ed25519.pub}
if [[ ! -f "$PUBKEY_PATH" ]]; then
  echo "Public key not found at $PUBKEY_PATH. Set PUBKEY_PATH env var or create an SSH key."
  echo "Generate one: ssh-keygen -t ed25519 -f $HOME/.ssh/id_ed25519 -N ''"
  exit 1
fi

for vm in "$@"; do
  echo "=== $vm ==="
  # Ensure ubuntu user exists and has sudo, then install authorized_keys
  limactl shell "$vm" sudo bash -c "\
    id -u ubuntu >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo ubuntu; \
    mkdir -p /home/ubuntu/.ssh; \
    chmod 700 /home/ubuntu/.ssh; \
    cat >> /home/ubuntu/.ssh/authorized_keys; \
    chown -R ubuntu:ubuntu /home/ubuntu/.ssh; \
    chmod 600 /home/ubuntu/.ssh/authorized_keys; \
    echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ubuntu; \
    chmod 0440 /etc/sudoers.d/ubuntu \
  " < "$PUBKEY_PATH"
  echo "OK: SSH key installed and sudoers configured"
Done
done
