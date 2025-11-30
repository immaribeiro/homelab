#!/usr/bin/env bash
set -euo pipefail
#!/bin/bash
set -euo pipefail

# Generate inventory with forwarded SSH and lima0 node_ip
# Usage: bash generate-inventory-from-limactl.sh > ../ansible/inventory.yml

get_port() {
  local name="$1"
  # limactl list --json outputs one JSON object per line
  limactl list --json | jq -r "select(.name==\"$name\") | .sshLocalPort"
}

get_lima0_ip() {
  local name="$1"
  limactl shell "$name" ip -4 addr show lima0 | awk '/inet/{print $2}' | cut -d'/' -f1
}

echo "all:"
echo "  children:"
echo "    control_plane:"
echo "      hosts:"

for name in $(limactl list --json | jq -r '.name' | grep '^k3s-control-'); do
  port=$(get_port "$name")
  ip=$(get_lima0_ip "$name")
  echo "        $name:"
  echo "          ansible_host: 127.0.0.1"
  echo "          ansible_port: $port"
  echo "          node_ip: $ip"
done

echo "    workers:"
echo "      hosts:"

for name in $(limactl list --json | jq -r '.name' | grep '^k3s-worker-'); do
  port=$(get_port "$name")
  ip=$(get_lima0_ip "$name")
  echo "        $name:"
  echo "          ansible_host: 127.0.0.1"
  echo "          ansible_port: $port"
  echo "          node_ip: $ip"
done

echo "  vars:"
echo "    ansible_user: \"ubuntu\""
echo "    ansible_ssh_common_args: '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'"
echo "    ansible_python_interpreter: /usr/bin/python3"
exit 0

  # Decide whether control plane or worker
  if [[ "$NAME" =~ k3s-control- ]]; then
    TARGET_SECTION="control_plane"
  elif [[ "$NAME" =~ k3s-worker- ]]; then
    TARGET_SECTION="workers"
  else
    TARGET_SECTION="workers"
  fi

  if [[ -n "$PORT" && "$PORT" != "0" ]]; then
    echo "        $NAME:" >> "$OUT_FILE"
    echo "          ansible_host: 127.0.0.1" >> "$OUT_FILE"
    echo "          ansible_port: $PORT" >> "$OUT_FILE"
  else
    # Try to get VM internal lima0 IP
    IP=$(limactl shell "$NAME" ip -4 addr show lima0 2>/dev/null | grep inet || true)
    if [[ -n "$IP" ]]; then
      IPADDR=$(echo "$IP" | awk '{print $2}' | cut -d'/' -f1)
      echo "        $IPADDR:" >> "$OUT_FILE"
    else
      echo "        # $NAME: could not determine address" >> "$OUT_FILE"
    fi
  fi

done

echo "Inventory generated: $OUT_FILE"
