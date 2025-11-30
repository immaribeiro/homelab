# Persistence Guide

Complete guide to persistent storage in your homelab cluster.

## Overview

All applications use persistent storage to ensure configurations, data, and state survive pod restarts, updates, and cluster reboots.

### Storage Architecture

**K3s Local Path Provisioner:**
- Automatic PVC provisioning using local node storage
- Default storage class: `local-path`
- Storage location on nodes: `/var/lib/rancher/k3s/storage/`
- Data persists across pod restarts and redeployments
- **Important:** Data is lost if you destroy VMs (use backups!)

## Application Persistence

### Home Assistant (5Gi)

**Persistent Data:**
- Configuration files (`configuration.yaml`, `automations.yaml`, etc.)
- Database (SQLite by default)
- Custom components
- User settings
- History and recorder data

**Location:** `/config` in container  
**PVC:** `home-assistant-config` in `home-assistant` namespace

**Access config:**
```bash
# View configuration
kubectl -n home-assistant exec deploy/home-assistant -- cat /config/configuration.yaml

# Edit configuration (example - requires text editor in container or copy out/in)
kubectl -n home-assistant cp home-assistant-<pod-id>:/config/configuration.yaml ./configuration.yaml
# Edit locally, then:
kubectl -n home-assistant cp ./configuration.yaml home-assistant-<pod-id>:/config/configuration.yaml
kubectl -n home-assistant rollout restart deploy/home-assistant
```

**Reset admin password:**
```bash
# Delete auth files to force new user creation
kubectl -n home-assistant exec deploy/home-assistant -- rm -f /config/.storage/auth*
kubectl -n home-assistant rollout restart deploy/home-assistant
# Access HA and create new admin account
```

### Plex (50Gi)

**Persistent Data:**
- Plex database and metadata
- User settings and preferences
- Watch history
- Library metadata and artwork
- Transcoding settings

**Location:** `/config` in container  
**PVC:** `plex-config` in `plex` namespace

**Note:** Media files use hostPath (`/Users/imma/plex`) - not in PVC

**Reset Plex:**
```bash
# To reclaim a server or reset preferences
kubectl -n plex exec deploy/plex -- rm -rf /config/Library/Application\ Support/Plex\ Media\ Server/Preferences.xml
kubectl -n plex rollout restart deploy/plex
```

### qBittorrent (1Gi config)

**Persistent Data:**
- qBittorrent settings (`qBittorrent.conf`)
- WebUI preferences
- Torrent state and queue
- Categories and tags
- RSS feeds

**Location:** `/config` in container  
**PVC:** `qbittorrent-config` in `qbittorrent` namespace

**Note:** Downloads use hostPath (`/Users/imma/torrents`) - not in PVC

**Reset WebUI password:**
```bash
# Edit config to remove password hash
kubectl -n qbittorrent exec deploy/qbittorrent -- sed -i 's/^WebUI\\Password_PBKDF2=.*/WebUI\\Password_PBKDF2=""/' /config/qBittorrent/qBittorrent.conf
kubectl -n qbittorrent rollout restart deploy/qbittorrent
# Default user: admin, password: adminadmin
```

**Alternative - find current password:**
```bash
# Get the WebUI password hash location
kubectl -n qbittorrent exec deploy/qbittorrent -- cat /config/qBittorrent/qBittorrent.conf | grep Password
```

### Homepage Dashboard (1Gi)

**Persistent Data:**
- `settings.yaml` - Dashboard settings
- `services.yaml` - Service definitions
- `widgets.yaml` - Widget configurations
- `bookmarks.yaml` - Bookmark links
- Custom icons and assets

**Location:** `/app/config` in container  
**PVC:** `homepage-config` in `homepage` namespace

**How it works:**
- First deployment: Copies defaults from ConfigMap to PVC
- Subsequent restarts: Preserves your custom configs in PVC
- Update defaults: Modify ConfigMap, delete PVC, redeploy

**Edit homepage configuration:**
```bash
# Method 1: Direct edit in pod
kubectl -n homepage exec -it deploy/homepage -- vi /app/config/services.yaml
kubectl -n homepage rollout restart deploy/homepage

# Method 2: Copy out, edit, copy in
kubectl -n homepage cp homepage-<pod-id>:/app/config/services.yaml ./services.yaml
# Edit locally
kubectl -n homepage cp ./services.yaml homepage-<pod-id>:/app/config/services.yaml
kubectl -n homepage rollout restart deploy/homepage

# Method 3: Use kubectl exec with cat/tee
kubectl -n homepage exec -i deploy/homepage -- tee /app/config/services.yaml <<EOF
- Media:
    - Plex:
        href: https://plex.immas.org
        icon: plex
EOF
kubectl -n homepage rollout restart deploy/homepage
```

**Reset to defaults:**
```bash
kubectl delete pvc homepage-config -n homepage
kubectl rollout restart deploy/homepage -n homepage
# Will recreate PVC and copy defaults
```

### Grafana (10Gi)

**Persistent Data:**
- Grafana database (SQLite)
- Custom dashboards
- Data sources
- User accounts and organizations
- Plugins
- Alerting rules

**Location:** `/var/lib/grafana` in container  
**PVC:** Automatically created by Helm chart as `kube-prometheus-stack-grafana`

**Admin password:**
- Stored in `grafana-admin` secret
- Set via `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` in `.env`
- Applied during `make metrics`

**Reset admin password:**
```bash
# Method 1: Update secret and restart
kubectl -n monitoring delete secret grafana-admin
export GRAFANA_ADMIN_PASSWORD="newpassword"
make metrics  # Recreates secret and updates deployment

# Method 2: Direct in Grafana database
kubectl -n monitoring exec -it deploy/kube-prometheus-stack-grafana -- grafana-cli admin reset-admin-password newpassword
kubectl -n monitoring rollout restart deploy/kube-prometheus-stack-grafana
```

**Access Grafana config:**
```bash
# View persistent data
kubectl -n monitoring exec deploy/kube-prometheus-stack-grafana -- ls -la /var/lib/grafana

# Backup Grafana database
kubectl -n monitoring exec deploy/kube-prometheus-stack-grafana -- tar czf - /var/lib/grafana > grafana-backup.tar.gz
```

### Prometheus (50Gi)

**Persistent Data:**
- Time-series metrics data (15 days retention)
- Recording rules state
- TSDB blocks

**Location:** `/prometheus` in container  
**PVC:** Automatically created by Helm as `prometheus-kube-prometheus-stack-prometheus-db-prometheus-kube-prometheus-stack-prometheus-0`

**Verify storage:**
```bash
kubectl -n monitoring exec -it prometheus-kube-prometheus-stack-prometheus-0 -- du -sh /prometheus
```

### Alertmanager (5Gi)

**Persistent Data:**
- Alert state
- Silences
- Notification history

**Location:** `/alertmanager` in container  
**PVC:** Automatically created by Helm as `alertmanager-kube-prometheus-stack-alertmanager-db-alertmanager-kube-prometheus-stack-alertmanager-0`

## Managing Persistent Volumes

### List All PVCs

```bash
# All namespaces
kubectl get pvc -A

# Specific namespace
kubectl get pvc -n home-assistant

# Detailed view
kubectl describe pvc homepage-config -n homepage
```

### Check PVC Usage

```bash
# Install df in pod (alpine-based)
kubectl -n home-assistant exec deploy/home-assistant -- df -h /config

# Or check on node directly
limactl shell k3s-control-1 sudo du -sh /var/lib/rancher/k3s/storage/pvc-*
```

### Resize PVC (if needed)

**Note:** K3s local-path provisioner doesn't support automatic resizing. To increase size:

```bash
# 1. Backup data
kubectl -n home-assistant exec deploy/home-assistant -- tar czf - /config > ha-config-backup.tar.gz

# 2. Delete deployment and PVC
kubectl delete deploy home-assistant -n home-assistant
kubectl delete pvc home-assistant-config -n home-assistant

# 3. Edit manifest with new size (e.g., 10Gi)
# Edit k8s/manifests/home-assistant.yml

# 4. Reapply
kubectl apply -f k8s/manifests/home-assistant.yml

# 5. Restore data
kubectl -n home-assistant cp ha-config-backup.tar.gz home-assistant-<pod-id>:/tmp/
kubectl -n home-assistant exec -it deploy/home-assistant -- tar xzf /tmp/ha-config-backup.tar.gz -C /
```

### Backup PVC Data

**Built-in backup target (Home Assistant & Plex):**
```bash
make backup
# Creates timestamped backups in backups/YYYYMMDD-HHMMSS/
```

**Manual backup of any PVC:**
```bash
# Generic backup command
NAMESPACE=homepage
DEPLOYMENT=homepage
MOUNT_PATH=/app/config
OUTPUT_FILE=homepage-config-backup.tar.gz

kubectl -n $NAMESPACE exec deploy/$DEPLOYMENT -- tar czf - $MOUNT_PATH > $OUTPUT_FILE
```

**Example backups:**
```bash
# Home Assistant
kubectl -n home-assistant exec deploy/home-assistant -- tar czf - /config > ha-backup.tar.gz

# Plex
kubectl -n plex exec deploy/plex -- tar czf - /config > plex-backup.tar.gz

# qBittorrent
kubectl -n qbittorrent exec deploy/qbittorrent -- tar czf - /config > qb-backup.tar.gz

# Homepage
kubectl -n homepage exec deploy/homepage -- tar czf - /app/config > homepage-backup.tar.gz

# Grafana
kubectl -n monitoring exec deploy/kube-prometheus-stack-grafana -- tar czf - /var/lib/grafana > grafana-backup.tar.gz
```

### Restore PVC Data

```bash
# Generic restore command
NAMESPACE=homepage
DEPLOYMENT=homepage
MOUNT_PATH=/app/config
BACKUP_FILE=homepage-config-backup.tar.gz

POD=$(kubectl -n $NAMESPACE get pod -l app=$DEPLOYMENT -o jsonpath='{.items[0].metadata.name}')
kubectl -n $NAMESPACE cp $BACKUP_FILE $POD:/tmp/backup.tar.gz
kubectl -n $NAMESPACE exec $POD -- tar xzf /tmp/backup.tar.gz -C /
kubectl -n $NAMESPACE rollout restart deploy/$DEPLOYMENT
```

## Persistence After Server Reboot

All PVC data survives Mac Mini reboots because:
1. Data is stored in VM disks (`/var/lib/rancher/k3s/storage/`)
2. Lima VM disks persist at `~/.lima/<vm-name>/`
3. Running `make post-reboot` starts VMs with existing disks intact

**What persists:**
- ✅ All application configs and databases
- ✅ Grafana dashboards and users
- ✅ Prometheus metrics (within 15d retention)
- ✅ Home Assistant automations and history
- ✅ Plex watch history and preferences
- ✅ qBittorrent torrents and queue state
- ✅ Homepage custom configurations

**What does NOT persist (by design):**
- ❌ `emptyDir` volumes (temporary, recreated on pod restart)
- ❌ Plex transcode cache (`/transcode` uses emptyDir)
- ❌ In-memory data

## Storage Locations Map

| Application | Config Path in Container | PVC Name | Size | Namespace |
|-------------|-------------------------|----------|------|-----------|
| Home Assistant | `/config` | `home-assistant-config` | 5Gi | `home-assistant` |
| Plex | `/config` | `plex-config` | 50Gi | `plex` |
| qBittorrent | `/config` | `qbittorrent-config` | 1Gi | `qbittorrent` |
| Homepage | `/app/config` | `homepage-config` | 1Gi | `homepage` |
| Grafana | `/var/lib/grafana` | `kube-prometheus-stack-grafana` | 10Gi | `monitoring` |
| Prometheus | `/prometheus` | `prometheus-...-db-prometheus-...-0` | 50Gi | `monitoring` |
| Alertmanager | `/alertmanager` | `alertmanager-...-db-alertmanager-...-0` | 5Gi | `monitoring` |

**HostPath Mounts (on Mac):**
| Path in Container | Mac Host Path | Purpose |
|-------------------|---------------|---------|
| `/data` (Plex) | `/Users/imma/plex` | Media files |
| `/downloads` (qBittorrent) | `/Users/imma/torrents` | Download directory |

## Disaster Recovery

### Full Cluster Backup Strategy

**1. Regular automated backups:**
```bash
# Add to cron (run daily at 2 AM)
0 2 * * * cd /Users/imma/GitHub/homelab && make backup
```

**2. Manual pre-maintenance backup:**
```bash
# Before major changes
make backup

# Backup monitoring stack
kubectl -n monitoring exec deploy/kube-prometheus-stack-grafana -- tar czf - /var/lib/grafana > backups/grafana-$(date +%Y%m%d).tar.gz
```

**3. Configuration in Git:**
- All manifests are version controlled
- `.env` excluded but documented in `ENV_VARS.md`
- Secrets should be backed up separately (1Password, etc.)

### Complete Recovery Procedure

If you lose all VMs but have backups:

```bash
# 1. Recreate cluster
make cluster-setup
make kubeconfig
make addons
make ingress-nginx
make tunnel
make metrics
make deploy-home

# 2. Deploy apps
kubectl apply -f k8s/manifests/home-assistant.yml
kubectl apply -f k8s/manifests/plex.yml
kubectl apply -f k8s/manifests/qbittorrent.yml

# 3. Wait for PVCs to be created
kubectl get pvc -A

# 4. Restore backups
# Home Assistant
kubectl -n home-assistant cp ha-backup.tar.gz <pod>:/tmp/
kubectl -n home-assistant exec <pod> -- tar xzf /tmp/ha-backup.tar.gz -C /

# Repeat for other apps

# 5. Restart deployments
kubectl rollout restart deploy/home-assistant -n home-assistant
kubectl rollout restart deploy/plex -n plex
# etc.
```

## Best Practices

1. **Regular Backups:**
   - Run `make backup` weekly (or add to cron)
   - Store backups off-cluster (external drive, cloud storage)

2. **Test Restores:**
   - Periodically verify backup integrity
   - Practice restore procedures

3. **Monitor Storage:**
   - Check PVC usage monthly
   - Plan for growth (especially Prometheus, Grafana, Plex)

4. **Document Changes:**
   - Note custom configs in Wiki or `docs/` folder
   - Keep `.env.example` updated with new variables

5. **Separate Concerns:**
   - Use PVCs for config/state (small, critical)
   - Use hostPath for large data (media, downloads)
   - Keep hostPath directories backed up separately

6. **Version Control:**
   - Commit manifest changes to Git
   - Tag releases for rollback capability

## Troubleshooting

### PVC Stuck in Pending

```bash
kubectl describe pvc <pvc-name> -n <namespace>
# Check events for errors

# Verify local-path provisioner
kubectl -n kube-system get pods | grep local-path
kubectl -n kube-system logs -l app=local-path-provisioner
```

### Cannot Write to Volume

```bash
# Check pod has correct permissions
kubectl -n <namespace> exec deploy/<deployment> -- ls -la <mount-path>

# Check storage on node
limactl shell k3s-control-1 df -h
```

### PVC Not Deleting

```bash
# Remove finalizers if stuck
kubectl patch pvc <pvc-name> -n <namespace> -p '{"metadata":{"finalizers":null}}'
```

### Data Corruption

```bash
# Stop deployment
kubectl scale deploy <deployment> -n <namespace> --replicas=0

# Restore from backup (see Restore section above)

# Restart
kubectl scale deploy <deployment> -n <namespace> --replicas=1
```

## Quick Reference

```bash
# List all PVCs and their sizes
kubectl get pvc -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,SIZE:.spec.resources.requests.storage,STORAGECLASS:.spec.storageClassName

# Total storage used by all PVCs
kubectl get pvc -A -o json | jq -r '.items[].spec.resources.requests.storage' | sed 's/Gi//' | awk '{sum+=$1} END {print sum " Gi total"}'

# Backup all app configs
make backup

# Verify persistence after restart
make post-reboot
kubectl get pvc -A
```
