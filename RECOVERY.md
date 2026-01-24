# Server Restart & Recovery Guide

Quick reference for recovering your homelab cluster after a Mac Mini reboot or power cycle.

## Important: Storage Initialization

Before or after cluster restart, ensure storage directories exist on all worker nodes:

```bash
# Initialize storage on all nodes
for node in k3s-worker-1 k3s-worker-2; do
  limactl shell $node sudo mkdir -p /var/lib/rancher/k3s/storage
  limactl shell $node sudo chmod 777 /var/lib/rancher/k3s/storage
done
```

If pods fail to mount volumes with errors like `MountVolume.NewMounter initialization failed`, this is likely the cause. See [Troubleshooting: Storage / PVC Mount Failures](./TROUBLESHOOTING.md#storage--pvc-mount-failures) for details.

## Quick Recovery (After Mac Mini Restart)

After your Mac Mini restarts, Lima VMs will be stopped. Run this single command to recover:

```bash
make post-reboot
```

This will:
1. Start all K3s VMs (`k3s-control-1`, `k3s-worker-1`, `k3s-worker-2`)
2. Wait for VMs to initialize
3. Fetch and configure kubeconfig
4. Wait for K3s to stabilize
5. Verify cluster health (nodes, pods, services)

**Expected time:** 60-90 seconds

## Manual Recovery Steps

If you prefer step-by-step control:

### 1. Start VMs
```bash
make start-vms
```

This starts all Lima VMs and waits for network initialization.

### 2. Update Kubeconfig
```bash
make kubeconfig
```

Fetches kubeconfig from the control plane and updates the server IP.

### 3. Verify Cluster
```bash
make verify-cluster
```

Checks health of:
- Nodes
- System pods (kube-system)
- MetalLB
- cert-manager
- Cloudflare Tunnel
- LoadBalancer services
- Certificates

### 4. Check Individual Services
```bash
# Homepage dashboard
kubectl -n homepage get pods
kubectl -n homepage logs deploy/homepage --tail=30

# Home Assistant
kubectl -n home-assistant get pods
kubectl -n home-assistant logs deploy/home-assistant --tail=30

# Plex
kubectl -n plex get pods

# qBittorrent
kubectl -n qbittorrent get pods

# Monitoring (Grafana/Prometheus)
kubectl -n monitoring get pods
```

## Common Post-Reboot Issues

### Issue: Cloudflare Tunnel Not Connecting

**Symptoms:**
- External URLs timing out
- `kubectl -n cloudflared logs deploy/cloudflared` shows connection errors

**Fix:**
```bash
# Restart the tunnel
kubectl -n cloudflared rollout restart deploy/cloudflared

# Wait 30s and check logs
sleep 30
kubectl -n cloudflared logs deploy/cloudflared --tail=50 | grep -i connected
```

### Issue: Pods Stuck in Pending or CrashLoopBackOff

**Check events:**
```bash
kubectl get events -A --sort-by='.lastTimestamp' | tail -20
```

**Common causes:**
- PVCs not mounting (storage issue)
- Node resources exhausted
- Image pull errors

**Fix:**
```bash
# Delete and recreate the pod
kubectl -n <namespace> delete pod <pod-name>

# Or restart the deployment
kubectl -n <namespace> rollout restart deployment/<deployment-name>
```

### Issue: LoadBalancer IP Not Assigned

**Check MetalLB:**
```bash
kubectl -n metallb-system get pods
kubectl -n metallb-system logs -l app=metallb --tail=50
```

**Fix:**
```bash
# Restart MetalLB speaker
kubectl -n metallb-system rollout restart daemonset/speaker
```

### Issue: Cannot Access Cluster (kubectl errors)

**Symptoms:**
- `The connection to the server <IP>:6443 was refused`
- `Unable to connect to the server: dial tcp`

**Fix:**
```bash
# Check if control plane is running
limactl list | grep k3s-control

# If stopped, start it
limactl start k3s-control-1

# Wait 30s for K3s to start
sleep 30

# Re-fetch kubeconfig
make kubeconfig

# Verify
kubectl cluster-info
```

### Issue: VMs Won't Start

**Check socket_vmnet:**
```bash
sudo brew services list | grep socket_vmnet
```

**If not running:**
```bash
sudo brew services start socket_vmnet
sleep 5
make start-vms
```

**Check Lima status:**
```bash
limactl list
```

**Force restart a stuck VM:**
```bash
limactl stop k3s-control-1 --force
sleep 2
limactl start k3s-control-1
```

## VM Management Commands

### Start/Stop Individual VMs
```bash
# Start specific VM
limactl start k3s-control-1

# Stop specific VM
limactl stop k3s-worker-1

# Stop all (graceful)
make stop-vms

# Start all
make start-vms

# Restart all
make restart-vms
```

### Check VM Status
```bash
# List all VMs with IPs
limactl list

# Get detailed VM info
limactl list --format '{{ .Name }}\t{{ .Status }}\t{{ .SSHLocalPort }}'

# SSH into a VM
limactl shell k3s-control-1
```

## Automated Startup on Mac Boot (Optional)

To automatically start VMs when your Mac Mini boots:

### Option 1: LaunchAgent (Recommended)

Create `~/Library/LaunchAgents/com.homelab.vms.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.homelab.vms</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-c</string>
        <string>cd /Users/imma/GitHub/homelab && /usr/bin/make start-vms</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/homelab-vms-startup.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/homelab-vms-startup.err</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.homelab.vms.plist
```

Unload (disable autostart):
```bash
launchctl unload ~/Library/LaunchAgents/com.homelab.vms.plist
```

### Option 2: Simple Shell Script

Create `~/start-homelab.sh`:

```bash
#!/bin/zsh
sleep 60  # Wait for network and services
cd /Users/imma/GitHub/homelab
make post-reboot &> /tmp/homelab-startup.log
```

Make executable:
```bash
chmod +x ~/start-homelab.sh
```

Add to **System Settings → General → Login Items** (macOS 13+) or use Automator.

## Health Check Script

Create a health check you can run anytime:

```bash
#!/bin/zsh
# Save as scripts/health-check.sh

echo "=== Homelab Health Check ==="
echo

echo "1. VM Status:"
limactl list
echo

echo "2. Cluster Nodes:"
kubectl get nodes -o wide
echo

echo "3. All Pods:"
kubectl get pods -A | grep -v Running | grep -v Completed || echo "✅ All pods Running/Completed"
echo

echo "4. Services with External IPs:"
kubectl get svc -A -o wide | grep -E 'NAMESPACE|LoadBalancer|ClusterIP.*:80'
echo

echo "5. Certificates:"
kubectl get certificates -A
echo

echo "6. Tunnel Status:"
kubectl -n cloudflared get pods
kubectl -n cloudflared logs deploy/cloudflared --tail=5 | grep -i "Registered tunnel connection" || echo "⚠️  Check tunnel logs"
echo

echo "7. Homepage:"
curl -I https://home.immas.org 2>&1 | head -5
echo

echo "=== Health Check Complete ==="
```

Make executable and run:
```bash
chmod +x scripts/health-check.sh
./scripts/health-check.sh
```

## Troubleshooting Checklist

After reboot, if things aren't working:

- [ ] socket_vmnet service running: `sudo brew services list | grep socket_vmnet`
- [ ] All VMs started: `limactl list` (should show "Running")
- [ ] Kubeconfig updated: `kubectl cluster-info`
- [ ] All nodes Ready: `kubectl get nodes`
- [ ] System pods Running: `kubectl get pods -n kube-system`
- [ ] MetalLB healthy: `kubectl get pods -n metallb-system`
- [ ] cert-manager healthy: `kubectl get pods -n cert-manager`
- [ ] Tunnel connected: `kubectl -n cloudflared logs deploy/cloudflared --tail=30`
- [ ] App pods Running: `kubectl get pods -A | grep -v Running`
- [ ] External access works: `curl -I https://home.immas.org`

## Make Targets Reference

| Target | Purpose |
|--------|---------|
| `make post-reboot` | **Full recovery** after Mac restart (recommended) |
| `make start-vms` | Start all Lima VMs |
| `make stop-vms` | Gracefully stop all VMs |
| `make restart-vms` | Stop then start all VMs |
| `make verify-cluster` | Check cluster health |
| `make kubeconfig` | Fetch and update kubeconfig |
| `make status` | Show nodes and pods via cluster-status.sh |

## Additional Resources

- **Main Setup:** [SETUP.md](./SETUP.md)
- **Deployment Guide:** [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Kubernetes Manifests:** [k8s/README.md](./k8s/README.md)

## Quick Commands Cheatsheet

```bash
# After Mac reboot
make post-reboot

# Manual recovery
make start-vms
make kubeconfig
make verify-cluster

# Check specific service
kubectl -n homepage get pods,svc
kubectl -n home-assistant logs deploy/home-assistant --tail=50

# Restart a service
kubectl -n cloudflared rollout restart deploy/cloudflared

# SSH into control plane
limactl shell k3s-control-1

# Full cluster status
make status

# Stop everything before shutdown
make stop-vms
```
