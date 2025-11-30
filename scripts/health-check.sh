#!/bin/zsh
# Health check script for homelab cluster

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
