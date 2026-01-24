# Changelog

All notable changes to the K3s Home Lab project are documented in this file.

## [0.2.0] - 2026-01-24

### Added
- **NGINX Ingress Controller Installation & Documentation** - Critical fix for ingress routing. Added step-by-step guide in DEPLOYMENT.md for installing NGINX Ingress Controller v1.11.1 as it's required for the manifests but not installed by default
- **Storage Initialization Guide** - Comprehensive documentation for initializing `/var/lib/rancher/k3s/storage/` on all worker nodes to fix PVC mount failures
- **Enhanced Troubleshooting Guides** - New sections for:
  - Storage / PVC Mount Failures with diagnosis and fixes
  - NGINX Ingress Controller not working with complete debugging steps
- **Improved RECOVERY.md** - Added storage initialization procedures as a critical first step after node restarts
- **Version badges in README** - Now shows latest release version for quick reference

### Fixed
- **Missing NGINX Ingress Controller** - Cluster went down because ingress controller was never installed; manifests expect NGINX but only Traefik (k3s default) was available
- **Missing Storage Directories** - PersistentVolume provisioner failed because `/var/lib/rancher/k3s/storage/` didn't exist on worker nodes; fixed 8+ pod mount failures
- **Stale PersistentVolumeClaims** - Old PVC references pointed to non-existent paths; recreated all PVCs with proper storage binding
- **Grafana PVC Issue** - Manually created missing PVC for kube-prometheus-stack-grafana

### Verified
- All 3 cluster nodes healthy and ready
- 38+ core pods running successfully
- All ingresses assigned LoadBalancer IP (192.168.105.50)
- Storage volumes properly mounted and functional
- Cloudflare Tunnel integration working
- TLS certificates valid and auto-renewed
- Monitoring stack (Prometheus, Grafana, Alertmanager) operational

### Documentation Updates
- Updated TROUBLESHOOTING.md with new diagnostic sections
- Updated DEPLOYMENT.md with critical NGINX installation step
- Updated RECOVERY.md with storage initialization procedures
- Updated README.md with version info and ingress controller highlights

### Known Issues
- Flightscanner deployment has nodeSelector mismatch (requires manual fix if needed)
- Two PVCs in Terminating state (old resources, safe to force-delete)

## [0.1.1] - Previous Release
- Initial k3s cluster setup with Lima VMs
- MetalLB and cert-manager configuration
- Cloudflare Tunnel integration
- Basic application deployments (Plex, Home Assistant, etc)
- Monitoring stack setup

## [0.1.0] - Initial Release
- K3s cluster foundation
- Terraform and Ansible automation
- Basic networking setup
