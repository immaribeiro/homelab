# Lima Environment

Defines VM templates and helper scripts used to run the K3s cluster locally on macOS.

## Templates
- `control-plane.yaml` – Higher availability / resources suitable for K3s server role.
- `worker.yaml` – Worker node configuration (reduced CPU/RAM).

Both templates:
- Use `vz` virtualization (Apple Virtualization.framework) on Apple Silicon.
- Attach `lima0` network for stable intra-VM communication (`192.168.105.0/24`).
- Rely on socket_vmnet for user-mode networking; avoid `eth0` for cluster traffic.

## Networking Rationale
`lima0` provides predictable L2 connectivity between VMs. `eth0` on the shared network is not bridged (ARP isolation), causing service discovery failures. All K3s flags are pinned to `lima0` (`--flannel-iface lima0`). MetalLB L2Advertisement also targets `lima0`.

## Scripts
- `create-vms.sh` – Rapid provisioning of control-plane + worker nodes.
- `destroy-vms.sh` – Remove instances cleanly.
- `teardown.sh` – Full cleanup including residual state.
- `bootstrap-ssh.sh` – Installs SSH public key & configures passwordless sudo.
- `cluster-status.sh` – Summary of VM and K3s health.
- `generate-inventory-from-limactl.sh` – Builds Ansible inventory mapping forwarded ports and `lima0` IPs.
- `fetch-kubeconfig.sh` – Pulls k3s kubeconfig from control node and patches server address.

## Typical Flow
```bash
bash lima/scripts/create-vms.sh 1 2
bash lima/scripts/bootstrap-ssh.sh k3s-control-1 k3s-worker-1 k3s-worker-2
bash lima/scripts/cluster-status.sh
```

## Maintenance Tips
- Use `limactl shell <vm> journalctl -u k3s -f` to inspect the K3s server.
- Keep disk usage in check; prune containers/images inside nodes occasionally.
- When changing template resources (CPU/RAM), recreate nodes for consistent behavior.

## Troubleshooting
If networking fails between nodes, confirm:
```bash
limactl shell k3s-worker-1 ping -c1 $(limactl shell k3s-control-1 hostname -I | awk '{print $1}')
```
If not reachable, verify `lima0` presence:
```bash
limactl shell k3s-worker-1 ip a | grep lima0
```
