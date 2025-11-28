#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

JSON_FILE="$SCRIPT_DIR/mock_outputs.json"
INVENTORY_FILE="$ROOT_DIR/ansible/inventory.yml"

echo "Writing mock Terraform outputs to $JSON_FILE"
cat > "$JSON_FILE" <<EOF
{
  "control_plane_ips": ["192.168.100.11"],
  "worker_ips": ["192.168.100.12", "192.168.100.13"]
}
EOF

echo "Writing sample Ansible inventory to $INVENTORY_FILE"
cat > "$INVENTORY_FILE" <<'YML'
all:
  children:
    control_plane:
      hosts:
        192.168.100.11:
    workers:
      hosts:
        192.168.100.12:
        192.168.100.13:
  vars:
    ansible_user: "ubuntu"
    ansible_ssh_common_args: '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
    ansible_python_interpreter: /usr/bin/python3
YML

echo "Mock Terraform apply complete."

echo "You can now run Ansible against the sample inventory:"
echo "  cd $ROOT_DIR/ansible && ansible-playbook -i inventory.yml playbooks/system-setup.yml"
