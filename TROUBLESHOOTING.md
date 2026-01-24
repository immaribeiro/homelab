# Troubleshooting Guide

Common issues and their solutions.

## Contents
1. [Storage / PVC Mount Failures](#storage--pvc-mount-failures)
2. [NGINX Ingress Controller Not Working](#nginx-ingress-controller-not-working)
3. [Networking / Lima](#networking--lima)
4. [MetalLB IP Not Assigned](#metallb-ip-not-assigned)
5. [Ingress 404 or Default Backend](#ingress-404-or-default-backend)
6. [Wildcard Certificate Pending](#wildcard-certificate-pending)
7. [Cloudflare DNS-01 Failures](#cloudflare-dns-01-failures)
8. [Tunnel Hostnames Not Resolving](#tunnel-hostnames-not-resolving)
9. [Tunnel Pod CrashLoopBackOff](#tunnel-pod-crashloopbackoff)
10. [Ansible SSH Failures](#ansible-ssh-failures)
11. [Homepage Dashboard Issues](#homepage-dashboard-issues)
12. [Monitoring Stack Issues](#monitoring-stack-issues)
13. [Grafana Password & Login](#grafana-password--login)
14. [Cloudflare DNS & VPN Resolvers](#cloudflare-dns--vpn-resolvers)

## Storage / PVC Mount Failures
- **Symptom:** Pods stuck in `Init:0/1` or `Pending` with error: `MountVolume.NewMounter initialization failed for volume "..."`.
- **Checks:**
```bash
kubectl describe pod <pod-name> -n <namespace> | grep -A 10 "Events:"
kubectl get pvc -n <namespace>
kubectl get pv | grep <pvc-name>
```
- **Root Cause:** The local-path provisioner storage directory `/var/lib/rancher/k3s/storage/` doesn't exist on the worker node.
- **Fix:** Create storage directories on all worker nodes:
```bash
# For each worker node (k3s-worker-1, k3s-worker-2, etc)
limactl shell k3s-worker-1 sudo mkdir -p /var/lib/rancher/k3s/storage
limactl shell k3s-worker-1 sudo chmod 777 /var/lib/rancher/k3s/storage
```
Then delete the failing PVC and pod to trigger recreation:
```bash
kubectl delete pvc <pvc-name> -n <namespace>
kubectl delete pod <pod-name> -n <namespace>
```

## NGINX Ingress Controller Not Working
- **Symptom:** Ingresses show no `ADDRESS` (blank or pending) after applying manifests.
- **Cause:** NGINX Ingress Controller was never installed. K3s includes Traefik by default, but your manifests are configured for NGINX.
- **Checks:**
```bash
kubectl get ingressclass
kubectl -n ingress-nginx get pods
kubectl -n ingress-nginx get svc
```
- **Fix:** Install NGINX Ingress Controller v1.11.1:
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.1/deploy/static/provider/cloud/deploy.yaml
kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=180s
```
Verify LoadBalancer IP assignment (should match MetalLB pool, e.g., `192.168.105.50`):
```bash
kubectl -n ingress-nginx get svc ingress-nginx-controller
```
Once installed, all ingresses will automatically be assigned the LoadBalancer IP.

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
dig -t txt _acme-challenge.immas.org
```
- Fix: Ensure no conflicting CNAME at apex; token not scoped to single zone unless intended.

## Tunnel Hostnames Not Resolving
- Symptom: `NXDOMAIN` for `hello.immas.org`.
- Checks:
```bash
dig +short hello.immas.org
```
- Fix: Add wildcard CNAME `*.lab` -> `<TUNNEL_ID>.cfargotunnel.com` OR explicit host route via `cloudflared tunnel route dns`.

## Cloudflare DNS & VPN Resolvers
- Symptom: Works on other devices, but your Mac shows `Could not resolve host` or HTTP 530 from Cloudflare.
- Cause: VPN (e.g., NordLynx) or per-interface DNS on macOS overrides/caches resolver responses; Ethernet and Wi‑Fi can use different resolvers.
- Fix:
   ```bash
   # Flush macOS DNS
   sudo dscacheutil -flushcache
   sudo killall -HUP mDNSResponder

   # Check resolvers
   scutil --dns | sed -n '1,120p'

   # Query Cloudflare resolver directly
   dig @1.1.1.1 +short sub.immas.org

   # Temporarily set Ethernet DNS to Cloudflare (replace with your service name)
   networksetup -setdnsservers "Ethernet" 1.1.1.1 1.0.0.1
   ```
   If still failing, verify the public hostname is attached to the Tunnel in Zero Trust → Tunnels → Public Hostnames, or rerun the route command using the tunnel name: `cloudflared tunnel route dns <TUNNEL_NAME> <host>`.

Notes:
- When testing edge routing, `curl --resolve host:443:<cf-ip>` can force hitting Cloudflare edge, but HTTP 530 indicates the hostname isn’t fully associated yet.
- The `cloudflare/cloudflared:latest` image is minimal; `cat` is not available in the container for exec checks.

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

## Homepage Dashboard Issues
- 500 error (EACCES / EROFS): ConfigMap volume is read-only. Confirm initContainer copies config into `emptyDir` at `/app/config` (see `k8s/manifests/home.yml`).
- Host validation failed: Set env `HOMEPAGE_ALLOWED_HOSTS=home.immas.org` in Deployment.
- Empty services/groups: Ensure `services.yaml` is a top-level list of groups (not nested under a `services:` key). Restart Deployment.
- Weather widget stuck on “Updating”: Verify latitude/longitude and label in `widgets.yaml`; restart Deployment.

## Monitoring Stack Issues
- Grafana login fails: Check `grafana-admin` Secret exists: `kubectl -n monitoring get secret grafana-admin` (created by `make metrics`).
- Prometheus targets down: Port-forward and open `/targets` to inspect label matching.
```bash
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
open http://localhost:9090/targets
```
- Alertmanager empty: Verify rules loaded: `kubectl -n monitoring get prometheusrules`; add alerting rules via Helm values.
- High resource usage: Lower scrape interval or disable exporters in `monitoring/values.yaml`.

## Grafana Password & Login

Understanding where the admin password comes from and how it’s applied:

- Helm values: The chart sets `.grafana.adminUser` and `.grafana.adminPassword` in `k8s/monitoring/values.yaml`.
- K8s secret: A Secret (`kube-prometheus-stack-grafana`) stores the admin password and is injected into the pod as `GF_SECURITY_ADMIN_USER` and `GF_SECURITY_ADMIN_PASSWORD`.
- Grafana DB: The persistent SQLite DB (`grafana.db`) stores the hashed password. UI changes write to this DB.

Effective behavior at startup:

- If `GF_SECURITY_ADMIN_PASSWORD` is present, Grafana initializes/overrides the admin password using that value at startup, regardless of what’s in the DB.
- If those env vars are not provided, the password in the DB remains in effect across restarts.

Symptoms you might see:

- Login succeeds once but fails after pod restart or chart upgrade.
- Password changed via UI reverts after a restart.
- Repeated failures lead to temporary lockout (brute-force protection).

Quick fixes

- Reset password now (DB only):
   - `make grafana-reset PASSWORD=<newpass>`
   - Takes effect immediately without a restart.
- Keep Helm and DB in sync (deterministic on restarts):
   - `make grafana-secret-sync PASSWORD=<newpass>`
   - Patches the Secret and restarts Deployment so the env matches the DB.

Diagnose the current source of truth

```bash
# 1) Check pod environment (does Grafana get admin creds via env?)
POD=$(kubectl -n monitoring get pods -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}')
kubectl -n monitoring exec "$POD" -- sh -lc 'env | grep ^GF_SECURITY_ADMIN_ || true'

# 2) Check the Secret value injected by Helm
kubectl -n monitoring get secret kube-prometheus-stack-grafana -o jsonpath='{.data.admin-password}' | base64 -d; echo

# 3) Confirm Deployment references the Secret env
kubectl -n monitoring get deploy kube-prometheus-stack-grafana -o yaml | grep -A2 GF_SECURITY_ADMIN
```

Make it deterministic (choose one model)

- Manage via Helm/Secret (recommended for GitOps):
   - Set `grafana.adminPassword: "<yourpass>"` in `k8s/monitoring/values.yaml`.
   - Apply: your normal `helm upgrade` flow.
   - Note: UI password changes won’t persist across pod restarts unless you also update the Helm value.
- Manage via UI/DB only (no env override):
   - Remove `grafana.adminUser` and `grafana.adminPassword` from `k8s/monitoring/values.yaml`.
   - Delete the Secret once to avoid leftover env overrides:
      ```bash
      kubectl -n monitoring delete secret kube-prometheus-stack-grafana || true
      kubectl -n monitoring rollout restart deploy/kube-prometheus-stack-grafana
      ```
   - Change the password in the UI; it will persist in the DB across restarts.

Lockouts and retries

- Too many failed attempts can trigger temporary lockout; wait a few minutes or restart the Grafana pod:
   ```bash
   kubectl -n monitoring rollout restart deploy/kube-prometheus-stack-grafana
   ```
- If needed temporarily, you can disable brute-force protection via Helm values with `GF_SECURITY_DISABLE_BRUTE_FORCE_LOGIN_PROTECTION=true` (not recommended for long-term).

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
