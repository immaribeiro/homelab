# Mock Terraform outputs

This folder contains helper artifacts to test the repo locally without running real Terraform/Lima.

Files:

- `mock_outputs.json` - JSON file containing mocked `control_plane_ips` and `worker_ips`.
- `mock_apply.sh` - Script that writes `mock_outputs.json` and updates `../ansible/inventory.yml` with the sample IPs.

Usage:

1. Make the script executable (if not already):

```bash
chmod +x mock_apply.sh
```

2. Run the script from the `terraform/` directory:

```bash
./mock_apply.sh
```

3. Run Ansible against the generated inventory:

```bash
cd ../ansible
ansible-playbook -i inventory.yml playbooks/system-setup.yml
```

Notes:
- This is a local mock to make it easy to test Ansible playbooks without creating Lima VMs.
- The IPs in `mock_outputs.json` are examples. Adjust them if you need to test different addresses.
