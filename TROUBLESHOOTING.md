# Troubleshooting Guide

## Networking: VMs can't reach each other


Common issues and their solutions.

## Contents
1. [Networking / Lima](#networking--lima)
2. [MetalLB IP Not Assigned](#metallb-ip-not-assigned)
3. [Ingress 404 or Default Backend](#ingress-404-or-default-backend)
4. [Wildcard Certificate Pending](#wildcard-certificate-pending)
5. [Cloudflare DNS-01 Failures](#cloudflare-dns-01-failures)
6. [Tunnel Hostnames Not Resolving](#tunnel-hostnames-not-resolving)
7. [Tunnel Pod CrashLoopBackOff](#tunnel-pod-crashloopbackoff)
8. [Ansible SSH Failures](#ansible-ssh-failures)

## Networking / Lima
- Symptom: Pods cannot reach services on `192.168.5.x` / `eth0`.
- Cause: Lima + socket_vmnet isolates `eth0`; ARP does not work VM-to-VM.
- Fix: Use `lima0` network only. Ensure K3s flags `--flannel-iface lima0` and inventory uses `lima0` IPs.

## MetalLB IP Not Assigned
- Symptom: `EXTERNAL-IP` shows `<pending>` for LoadBalancer service.
- Checks:
```bash
kubectl -n metallb-system get pods
kubectl describe ipaddresspool -n metallb-system
kubectl get l2advertisements -n metallb-system
```
- Common causes:
   - IP pool overlaps with node IPs.
   - Missing L2Advertisement or wrong interface (should be lima0).
- Fix: Adjust `k8s/metallb/metallb-config.yaml`; reapply and check logs.

## Ingress 404 or Default Backend
- Symptom: HTTPS returns default backend 404.
- Checks:
```bash
kubectl -n ingress-nginx get pods
kubectl get ingress -A
kubectl describe ingress home
```
- Causes:
   - Host mismatch.
   - TLS secret in wrong namespace.
   - Service name / port mismatch.
- Fix: Align Ingress host with DNS, ensure backend service exists, secret is in same namespace.

## Wildcard Certificate Pending
- Symptom: `kubectl describe certificate` shows challenge stuck.
- Checks:
```bash
kubectl -n cert-manager get challenges.acme.cert-manager.io
kubectl -n cert-manager logs deploy/cert-manager | grep -i cloudflare
```
- Causes:
   - Missing Zone.Zone:Read permission on API token.
   - DNS propagation delay.
- Fix: Recreate token with `Zone.DNS` + `Zone.Zone` for the zone; wait or add recursive nameservers flag to deployment.

## Cloudflare DNS-01 Failures
- Symptom: ACME error: authorization failed.
- Checks: Validate TXT record externally:
```bash
dig -t txt _acme-challenge.lab.immas.org
```
- Fix: Ensure no conflicting CNAME at apex; token not scoped to single zone unless intended.

## Tunnel Hostnames Not Resolving
- Symptom: `NXDOMAIN` for `hello.lab.immas.org`.
- Checks:
```bash
dig +short hello.lab.immas.org
```
- Fix: Add wildcard CNAME `*.lab` -> `<TUNNEL_ID>.cfargotunnel.com` OR explicit host route via `cloudflared tunnel route dns`.

## Tunnel Pod CrashLoopBackOff
- Symptom: `kubectl -n cloudflared get pods` shows restarting.
- Checks:
```bash
kubectl -n cloudflared logs deploy/cloudflared --tail=50
```
- Causes:
   - Wrong credentials JSON.
   - Missing `TUNNEL_ID` env.
   - Malformed ConfigMap.
- Fix: Recreate secret from correct file; verify ConfigMap keys `tunnel` and `credentials-file`.

## Ansible SSH Failures
- Symptom: Timeout or permission denied.
- Checks:
   - Inventory host/port matches `limactl list` forwarded port.
   - SSH key installed via `bootstrap-ssh.sh`.
- Fix: Re-run bootstrap, ensure correct user (`ubuntu`), and remove stale known_hosts entries.

## socket_vmnet Issues

### Error: "/opt/socket_vmnet/bin/socket_vmnet" has to be installed

**Cause:** socket_vmnet binary is not at the expected location.

**Solution:**

```bash
# Find socket_vmnet version
SOCKET_VERSION=$(ls /opt/homebrew/Cellar/socket_vmnet/ | head -1)

# Create directory and copy binary
sudo mkdir -p /opt/socket_vmnet/bin
- Symptom: Workers fail to join; `curl` to control plane `:6443` from workers times out; `ping` to `192.168.5.x` shows "Destination Host Unreachable"; `ip neigh show dev eth0` shows `FAILED` for peer IPs.
- Root cause: Lima `shared` (socket_vmnet) does not bridge `eth0` VM-to-VM on `192.168.5.0/24`. DHCP may also assign the same IP to multiple VMs.
- Fix:
   - Use `lima0` network (`192.168.105.x`) for K3s cluster communication.
   - Set K3s flags to use `lima0`: `--flannel-iface lima0`, `--node-ip <lima0-ip>`, `--node-external-ip <lima0-ip>`.
   - Agents: set `K3S_AGENT_BOOTSTRICT_MODE=false` to bypass localhost-only supervisor bootstrap.
   - Inventory: keep Ansible over `127.0.0.1:<port>` forwarded SSH; include `node_ip` as the `lima0` IP per host.

### Verify

```bash
# From macOS host
bash lima/scripts/cluster-status.sh

# From worker VM, reach control plane over lima0
limactl shell k3s-worker-1 ping -c 2 192.168.105.2
```

### References

- `SETUP.md` → Networking section for the working topology and commands.
sudo cp /opt/homebrew/Cellar/socket_vmnet/$SOCKET_VERSION/bin/socket_vmnet /opt/socket_vmnet/bin/socket_vmnet

# Verify
ls -la /opt/socket_vmnet/bin/socket_vmnet
```

### Error: socket_vmnet service not running

**Check status:**

```bash
sudo brew services list | grep socket_vmnet
```

**Start socket_vmnet:**

```bash
sudo brew services start socket_vmnet

# Wait a moment for it to start
sleep 2

# Verify
sudo brew services list | grep socket_vmnet
```

### Warning: "Both top-level 'rosetta' and 'vmOpts.vz.rosetta' are configured"

**Cause:** Old VM configuration still exists with deprecated rosetta settings.

**Solution:**

```bash
# Delete old VMs
limactl delete k3s-control-1
limactl delete k3s-worker-1 k3s-worker-2

# Remove configuration directories
rm -rf ~/.lima/k3s-*

# Recreate VMs with fixed templates
bash lima/scripts/create-vms.sh 1 2
```

## VM Creation Issues

### Error: instance already exists

**Cause:** VM configuration already exists from previous attempt.

**Solution:**

```bash
# List existing VMs
limactl list

# Delete specific VM
limactl delete k3s-control-1

# Or remove all k3s VMs
rm -rf ~/.lima/k3s-*

# Recreate
bash lima/scripts/create-vms.sh 1 2
```

### Error: "can't read '/private/etc/sudoers.d/lima'"

**Cause:** Lima sudoers not configured.

**Solution:**

```bash
limactl sudoers > /tmp/etc_sudoers.d_lima
sudo install -o root /tmp/etc_sudoers.d_lima "/private/etc/sudoers.d/lima"
rm /tmp/etc_sudoers.d_lima
```

### VMs stuck in "Stopped" state

**Solution:**

```bash
# Start the VM
limactl start k3s-control-1

# Wait a moment
sleep 10

# Check status
limactl list

# If still stuck, try restart
limactl stop k3s-control-1
sleep 2
limactl start k3s-control-1
```

## Network Issues

### VMs cannot communicate with each other

**Verify socket_vmnet is running:**

```bash
sudo brew services list | grep socket_vmnet
```

**Check network interface inside VM:**

```bash
limactl shell k3s-control-1 ip addr show lima0

# Should show an IP like 192.168.x.x on lima0 interface
```

**Test connectivity:**

```bash
# Get worker IP
WORKER_IP=$(limactl shell k3s-worker-1 hostname -I | awk '{print $1}')

# Ping from control plane to worker
limactl shell k3s-control-1 ping -c 3 $WORKER_IP

# Should succeed
```

**If ping fails:**

```bash
# Check if socket_vmnet service is actually running
sudo launchctl list | grep socket_vmnet

# Check for interface
ifconfig | grep -A 5 vlan

# Restart socket_vmnet
sudo brew services restart socket_vmnet
sleep 5

# Restart VMs
limactl stop k3s-control-1 k3s-worker-1 k3s-worker-2
sleep 5
limactl start k3s-control-1 k3s-worker-1 k3s-worker-2
```

### No IP assigned to lima0 interface

**Verify network configuration in VM:**

```bash
limactl shell k3s-control-1

# Inside VM, check if DHCP is working
sudo dhclient lima0
ip addr show lima0
```

**Check VM yaml configuration:**

```bash
# Verify the network section is correct
cat /tmp/k3s-control-1.yaml | grep -A 5 networks:

# Should show:
# networks:
#   - lima: shared
#     interface: lima0
```

## Ansible Issues

### Error: "Failed to connect to host"

**Cause:** Inventory IP addresses are incorrect or VMs not ready.

**Solution:**

```bash
# Verify VMs are running
limactl list

# Check actual VM IPs
limactl shell k3s-control-1 ip -4 addr show lima0 | grep inet
limactl shell k3s-worker-1 ip -4 addr show lima0 | grep inet

# Update inventory.yml with correct IPs
nano ansible/inventory.yml

# Test connectivity
ansible -i ansible/inventory.yml all -m ping
```

### Error: "Host key is not allowed in /etc/ssh/ssh_config"

**Solution:**

```bash
# Update ansible.cfg
cat >> ansible/ansible.cfg << 'EOF'
host_key_checking = False
EOF

# Retry playbook
ansible-playbook -i inventory.yml playbooks/k3s-install.yml
```

### Ansible playbook hangs

**Check what's happening:**

```bash
# In another terminal, SSH into the VM
limactl shell k3s-control-1

# Check if K3s installation is running
ps aux | grep k3s
sudo journalctl -u k3s -f

# Check disk space
df -h

# Check memory
free -h
```

**Increase Ansible timeout:**

```bash
# Edit ansible.cfg
cat >> ansible/ansible.cfg << 'EOF'
timeout = 60
EOF
```

## K3s Issues

### Nodes showing "NotReady" status

```bash
# SSH into control plane
limactl shell k3s-control-1

# Check K3s status
sudo systemctl status k3s

# Check K3s logs
sudo journalctl -u k3s -f

# Check node status in detail
kubectl describe node k3s-control-1

# Check pod status
kubectl get pods -A
```

### kubeconfig access issues

**Problem: Cannot connect to cluster**

```bash
# Verify kubeconfig exists and is readable
cat ~/.kube/config

# Check the server IP
grep server ~/.kube/config

# It should point to your control plane IP, not 127.0.0.1
```

**Fix kubeconfig:**

```bash
# Get control plane IP
CONTROL_IP=$(limactl shell k3s-control-1 ip -4 addr show lima0 | grep inet | awk '{print $2}' | cut -d'/' -f1)

# Update kubeconfig
sed -i '' "s/127.0.0.1/$CONTROL_IP/g" ~/.kube/config

# Verify
kubectl cluster-info
```

### CoreDNS or Flannel pods not running

```bash
# Check pod status
kubectl get pods -n kube-system
kubectl get pods -n kube-flannel

# Describe problematic pod
kubectl describe pod <pod-name> -n kube-system

# Check logs
kubectl logs <pod-name> -n kube-system
```

### Pods stuck in "Pending" state

```bash
# Check node capacity
kubectl describe nodes

# Check if there are resource constraints
kubectl describe pod <pod-name>

# Check node disk space
limactl shell k3s-control-1 df -h
```

## Performance Issues

### VMs running slowly

**Check available resources:**

```bash
# Check Mac CPU usage
top -b -n 1 | head -20

# Check memory
vm_stat

# Inside VM, check resource allocation
limactl shell k3s-control-1 free -h
limactl shell k3s-control-1 nproc
```

**Solutions:**

1. Close unnecessary applications on Mac
2. Increase VM resources (edit terraform.tfvars):
   ```hcl
   # lima/templates/control-plane.yaml
   cpus: 4        # Increase from 2
   memory: "8GiB" # Increase from 4GiB
   ```
3. Increase disk allocation if running low

### High memory usage

```bash
# Check what's consuming memory in VMs
limactl shell k3s-control-1 top -b -n 1

# Check K3s component sizes
kubectl top nodes
kubectl top pods -A
```

## Cleanup and Reset

### Complete cleanup

```bash
# Delete Terraform resources
cd terraform
terraform destroy

# Remove VM configs
rm -rf ~/.lima/k3s-*

# Remove kubeconfig
rm ~/.kube/config

# Remove socket_vmnet (optional, if not using Lima for other projects)
# brew uninstall socket_vmnet
# sudo brew services stop socket_vmnet
```

### Fresh start after failed setup

```bash
# Kill any stuck processes
killall lima 2>/dev/null || true

# Remove everything
rm -rf ~/.lima/k3s-*
rm -f ~/.kube/config

# Rerun setup
bash setup.sh
```

## Getting Help

### Collect debugging information

```bash
# Create debug log
mkdir -p ~/homelab-debug

# Gather system info
echo "=== System Info ===" > ~/homelab-debug/debug.log
system_profiler SPHardwareDataType >> ~/homelab-debug/debug.log

# Gather Lima info
echo "=== Lima Info ===" >> ~/homelab-debug/debug.log
limactl list -l >> ~/homelab-debug/debug.log

# Gather K3s info
echo "=== K3s Status ===" >> ~/homelab-debug/debug.log
kubectl get nodes -o wide >> ~/homelab-debug/debug.log 2>&1
kubectl get pods -A >> ~/homelab-debug/debug.log 2>&1

# Check socket_vmnet
echo "=== socket_vmnet Status ===" >> ~/homelab-debug/debug.log
sudo brew services list | grep socket_vmnet >> ~/homelab-debug/debug.log

# Share debug log when asking for help
cat ~/homelab-debug/debug.log
```

## Still having issues?

1. Check Lima documentation: https://github.com/lima-vm/lima
2. Check K3s documentation: https://docs.k3s.io/
3. Review Ansible documentation: https://docs.ansible.com/
4. Check Terraform documentation: https://www.terraform.io/docs/
