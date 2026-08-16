#!/bin/bash
# Fix stale K3S_URL on workers — point to correct control plane IP
for worker in k3s-worker-1 k3s-worker-2; do
  echo "Fixing $worker..."
  limactl shell "$worker" sudo sed -i 's|192.168.5.15|192.168.5.10|' /etc/systemd/system/k3s-agent.service.env
  limactl shell "$worker" sudo systemctl daemon-reload
  limactl shell "$worker" sudo systemctl restart k3s-agent
  echo "Done with $worker"
done
echo "All workers fixed."
