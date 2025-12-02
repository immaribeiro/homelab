# ArgoCD - GitOps for Homelab

ArgoCD provides declarative, Git-based continuous delivery for Kubernetes.

## Installation

```bash
# Install ArgoCD
make argocd

# Get admin password
make argocd-password

# Access UI
# Internal: kubectl -n argocd port-forward svc/argocd-server 8080:443
# External: https://argocd.immas.org (via Cloudflare Tunnel)
```

## Initial Setup

1. **Install ArgoCD:**
   ```bash
   make argocd
   ```

2. **Get admin password:**
   ```bash
   make argocd-password
   ```

3. **Access UI:**
   - External: https://argocd.immas.org
   - Username: `admin`
   - Password: (from previous step)

4. **Optional: Change password via CLI:**
   ```bash
   argocd login argocd.immas.org
   argocd account update-password
   ```

## Architecture

This setup uses an "app-of-apps" pattern:
- `argocd/apps/root.yaml` - Root application that manages all other apps
- `argocd/apps/*.yaml` - Individual application definitions
- Each app points to manifests in `k8s/manifests/`

## Managing Applications

### Add a new application via ArgoCD

Create a file in `argocd/apps/`:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/immaribeiro/homelab.git
    targetRevision: main
    path: k8s/manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Manual sync
```bash
argocd app sync my-app
```

### Check status
```bash
argocd app list
argocd app get my-app
```

## Features Enabled

- **Auto-sync:** Apps sync automatically on Git push
- **Self-heal:** Drift is automatically corrected
- **Prune:** Deleted resources are removed from cluster
- **Web UI:** Visual application management
- **CLI:** `argocd` command-line tool

## Troubleshooting

### Can't access UI
```bash
# Check pod status
kubectl -n argocd get pods

# Check service
kubectl -n argocd get svc argocd-server

# Port-forward for local access
kubectl -n argocd port-forward svc/argocd-server 8080:443
open https://localhost:8080
```

### Password doesn't work
```bash
# Get fresh password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo

# Reset password
kubectl -n argocd delete secret argocd-initial-admin-secret
kubectl -n argocd rollout restart deployment argocd-server
```

### App won't sync
```bash
# Check sync status
argocd app get my-app

# Force sync
argocd app sync my-app --force

# Check logs
kubectl -n argocd logs -l app.kubernetes.io/name=argocd-application-controller --tail=100
```

## Best Practices

1. **Use branches for testing:** Create feature branches and test apps before merging to main
2. **Health checks:** Define custom health checks for complex apps
3. **Sync waves:** Use annotations to control deployment order
4. **Secrets management:** Consider Sealed Secrets or External Secrets for sensitive data
5. **Backup:** Regularly export ArgoCD app definitions

## Next Steps

- Install ArgoCD CLI: `brew install argocd`
- Set up SSO (optional): Configure GitHub/Google OAuth
- Add monitoring: ArgoCD metrics → Prometheus → Grafana dashboards
- Integrate with CI: Auto-create/update apps from CI pipelines
