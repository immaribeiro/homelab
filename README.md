# K3s Home Lab on Mac Mini M4 (Lima-based)

Complete Infrastructure-as-Code setup for a K3s cluster using Lima, Terraform, and Ansible with proper networking.

## Quick Start

```bash
# Run automated setup
bash setup.sh

# Then create VMs and install K3s
cd terraform && terraform init && terraform apply
cd ../ansible && ansible-playbook -i inventory.yml playbooks/k3s-install.yml
```

See [SETUP.md](./SETUP.md) for detailed instructions, [k8s/README.md](./k8s/README.md) for manifest conventions, [lima/README.md](./lima/README.md) for VM environment, [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues, and [RECOVERY.md](./RECOVERY.md) for server restart procedures.

## Architecture Overview

Core + Add-on Components:
- Lima VMs (control-plane + workers) on `lima0` network.
- K3s lightweight Kubernetes distribution.
- MetalLB for LoadBalancer IP assignment (pool `192.168.105.50-99`).
- cert-manager with Cloudflare DNS-01 for wildcard TLS.
- NGINX Ingress Controller for HTTP routing (when hostnames are terminated internally).
- Cloudflare Tunnel for outbound-only external access (no inbound firewall/NAT required).
- Monitoring stack: Prometheus, Alertmanager, Grafana (`monitoring` namespace).
- Central dashboard: Homepage (`homepage` namespace) aggregating links & widgets.
- Media & apps: Plex (`plex`), Home Assistant (`home-assistant`), qBittorrent (`qbittorrent`).
- Application manifests under `k8s/manifests/` using shared wildcard TLS secret.

Namespace inventory with purposes is documented in `k8s/README.md`.

Default Flow (Tunnel mapping to Cluster):
Client → Cloudflare (wildcard CNAME) → Cloudflare Tunnel → (Ingress-NGINX or direct Service) → Pod

Monitoring (Grafana) is exposed through the Tunnel; Prometheus/Alertmanager remain internal unless explicitly routed.

## Add-ons & Operations Automation
```bash
make addons          # MetalLB + cert-manager + issuers + wildcard cert
make ingress-nginx   # Install ingress controller
make deploy-home     # Deploy home app + ingress
make tunnel          # Deploy cloudflared (requires env vars)
make metrics         # Install kube-prometheus-stack (Prometheus/Grafana)
```

Verify:
```bash
kubectl get nodes
kubectl get svc -A | grep LoadBalancer
kubectl get certificates -A
kubectl get ingress -A
```

## Prerequisites

```bash
# Install required tools on macOS
brew install lima terraform ansible

# Install socket_vmnet for proper VM networking (REQUIRED for K3s)
brew install socket_vmnet
sudo brew services start socket_vmnet

# Copy socket_vmnet binary to location where Lima expects it
SOCKET_VERSION=$(ls /opt/homebrew/Cellar/socket_vmnet/ | head -1)
sudo mkdir -p /opt/socket_vmnet/bin
sudo cp /opt/homebrew/Cellar/socket_vmnet/$SOCKET_VERSION/bin/socket_vmnet /opt/socket_vmnet/bin/socket_vmnet

# Configure sudoers for Lima (required for VM management)
limactl sudoers > /tmp/etc_sudoers.d_lima
sudo install -o root /tmp/etc_sudoers.d_lima "/private/etc/sudoers.d/lima"

# Verify socket_vmnet is running
sudo brew services list | grep socket_vmnet
```

## Why socket_vmnet?

Lima's default networking uses user-mode (slirp) which doesn't allow VM-to-VM communication. For K3s, you need VMs to talk to each other. `socket_vmnet` provides:
- Bridge networking between VMs
- VM-to-VM communication
- Stable IP addresses
- Proper network for K3s CNI plugins

## Quick Cluster Check
After installing K3s, you can quickly verify the cluster with:

```sh
# From repo root
make status
```

The status target runs `lima/scripts/cluster-status.sh` to print `kubectl get nodes -o wide` and `kubectl get pods -A` from the control plane VM.

## Cloudflare Tunnel DNS Setup
To access apps (e.g. `hello.immas.org`) from any device without `/etc/hosts` hacks:

1. Create tunnel locally:
  ```sh
  cloudflared tunnel login
  cloudflared tunnel create homelab
  export TUNNEL_ID=<uuid output>
  ```
2. Add DNS route (automatic CNAME creation):
  ```sh
  cloudflared tunnel route dns homelab hello.immas.org
  # Or wildcard:
  cloudflared tunnel route dns homelab '*.immas.org'
  ```
3. Deploy tunnel in cluster (from repo root):
  ```sh
  export TUNNEL_CRED_FILE=~/.cloudflared/$TUNNEL_ID.json
  make tunnel
  ```
4. Verify tunnel pod:
  ```sh
  kubectl -n cloudflared get pods
  kubectl -n cloudflared logs deploy/cloudflared | tail -n 40
  ```
5. Test external access (from a different network/device):
  ```sh
  curl -I https://hello.immas.org
  ```

Notes:
- Wildcard CNAME (`*.immas.org`) lets you map multiple subdomains using one Tunnel.
- Ingress rules are defined in `k8s/cloudflared/tunnel.yaml` ConfigMap; add new hostnames under `ingress:` list.
- Keep a final catch-all rule: `- service: http_status:404`.
- SSL termination still handled by NGINX Ingress with your wildcard Let’s Encrypt certificate.


## Repository Structure

```
k3s-homelab/
├── README.md
├── lima/
│   ├── templates/
│   │   ├── control-plane.yaml
│   │   └── worker.yaml
│   └── scripts/
│       ├── create-vms.sh
│       └── destroy-vms.sh
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars
├── ansible/
│   ├── ansible.cfg
│   ├── inventory.yml
│   ├── playbooks/
│   │   ├── k3s-install.yml
│   │   ├── k3s-reset.yml
│   │   └── system-setup.yml
│   └── group_vars/
│       └── all.yml
└── k8s/
    └── manifests/
        └── example-app.yml
```

## Step 1: Lima VM Templates

### lima/templates/control-plane.yaml
```yaml
# VM type
vmType: "vz"
vmOpts:
  vz:
    rosetta: false

# CPU and Memory
cpus: 2
memory: "4GiB"
disk: "20GiB"

# Image
images:
  - location: "https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-arm64.img"
    arch: "aarch64"

# Network - CRITICAL for K3s
networks:
  - lima: shared
    macAddress: "52:55:55:00:00:01"
    interface: "lima0"

# Mounts
mounts:
  - location: "~"
    writable: false

# SSH
ssh:
  localPort: 0
  loadDotSSHPubKeys: true
  forwardAgent: false

# Provisioning
provision:
  - mode: system
    script: |
      #!/bin/bash
      set -eux -o pipefail
      
      # Update system
      apt-get update
      apt-get install -y curl vim net-tools
      
      # Disable swap (required for K8s)
      swapoff -a
      sed -i '/swap/d' /etc/fstab
      
      # Enable IP forwarding
      cat <<EOF > /etc/sysctl.d/k8s.conf
      net.ipv4.ip_forward = 1
      net.bridge.bridge-nf-call-iptables = 1
      net.bridge.bridge-nf-call-ip6tables = 1
      EOF
      sysctl --system
      
      # Set hostname
      hostnamectl set-hostname k3s-control-1

# Kernel modules for K8s
provision:
  - mode: system
    script: |
      #!/bin/bash
      modprobe br_netfilter
      modprobe overlay
      cat <<EOF > /etc/modules-load.d/k8s.conf
      br_netfilter
      overlay
      EOF

containerd:
  system: false
  user: false
```

### lima/templates/worker.yaml
```yaml
# VM type
vmType: "vz"
vmOpts:
  vz:
    rosetta: false

# CPU and Memory
cpus: 2
memory: "3GiB"
disk: "15GiB"

# Image
images:
  - location: "https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-arm64.img"
    arch: "aarch64"

# Network - CRITICAL for K3s
# NOTE: Change macAddress for each worker
networks:
  - lima: shared
    macAddress: "52:55:55:00:00:02"
    interface: "lima0"

# Mounts
mounts:
  - location: "~"
    writable: false

# SSH
ssh:
  localPort: 0
  loadDotSSHPubKeys: true
  forwardAgent: false

# Provisioning
provision:
  - mode: system
    script: |
      #!/bin/bash
      set -eux -o pipefail
      
      # Update system
      apt-get update
      apt-get install -y curl vim net-tools
      
      # Disable swap
      swapoff -a
      sed -i '/swap/d' /etc/fstab
      
      # Enable IP forwarding
      cat <<EOF > /etc/sysctl.d/k8s.conf
      net.ipv4.ip_forward = 1
      net.bridge.bridge-nf-call-iptables = 1
      net.bridge.bridge-nf-call-ip6tables = 1
      EOF
      sysctl --system
      
      # Set hostname (will be overridden by script)
      hostnamectl set-hostname k3s-worker-1

provision:
  - mode: system
    script: |
      #!/bin/bash
      modprobe br_netfilter
      modprobe overlay
      cat <<EOF > /etc/modules-load.d/k8s.conf
      br_netfilter
      overlay
      EOF

containerd:
  system: false
  user: false
```

## Step 2: Lima Management Scripts

### lima/scripts/create-vms.sh
```bash
#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TEMPLATE_DIR="$SCRIPT_DIR/../templates"

# Configuration
CONTROL_PLANE_COUNT=${1:-1}
WORKER_COUNT=${2:-2}

echo "Creating K3s cluster with Lima..."
echo "Control planes: $CONTROL_PLANE_COUNT"
echo "Workers: $WORKER_COUNT"

# Create control plane nodes
for i in $(seq 1 $CONTROL_PLANE_COUNT); do
    VM_NAME="k3s-control-$i"
    echo "Creating $VM_NAME..."
    
    # Copy template and customize
    cp "$TEMPLATE_DIR/control-plane.yaml" "/tmp/$VM_NAME.yaml"
    
    # Update hostname in template
    sed -i '' "s/k3s-control-1/$VM_NAME/g" "/tmp/$VM_NAME.yaml"
    
    # Update MAC address (increment last octet)
    MAC_SUFFIX=$(printf "%02d" $i)
    sed -i '' "s/52:55:55:00:00:01/52:55:55:00:00:$MAC_SUFFIX/g" "/tmp/$VM_NAME.yaml"
    
    # Create VM
    limactl start --name="$VM_NAME" "/tmp/$VM_NAME.yaml"
    
    echo "$VM_NAME created successfully"
done

# Create worker nodes
for i in $(seq 1 $WORKER_COUNT); do
    VM_NAME="k3s-worker-$i"
    echo "Creating $VM_NAME..."
    
    # Copy template and customize
    cp "$TEMPLATE_DIR/worker.yaml" "/tmp/$VM_NAME.yaml"
    
    # Update hostname
    sed -i '' "s/k3s-worker-1/$VM_NAME/g" "/tmp/$VM_NAME.yaml"
    
    # Update MAC address (start from 10 to avoid conflicts)
    MAC_SUFFIX=$(printf "%02d" $((10 + i)))
    sed -i '' "s/52:55:55:00:00:02/52:55:55:00:00:$MAC_SUFFIX/g" "/tmp/$VM_NAME.yaml"
    
    # Create VM
    limactl start --name="$VM_NAME" "/tmp/$VM_NAME.yaml"
    
    echo "$VM_NAME created successfully"
done

echo ""
echo "All VMs created! Waiting for network initialization..."
sleep 10

echo ""
echo "VM List:"
limactl list

echo ""
echo "Getting VM IPs..."
for i in $(seq 1 $CONTROL_PLANE_COUNT); do
    VM_NAME="k3s-control-$i"
    IP=$(limactl shell "$VM_NAME" ip -4 addr show lima0 | grep inet | awk '{print $2}' | cut -d'/' -f1)
    echo "$VM_NAME: $IP"
done

for i in $(seq 1 $WORKER_COUNT); do
    VM_NAME="k3s-worker-$i"
    IP=$(limactl shell "$VM_NAME" ip -4 addr show lima0 | grep inet | awk '{print $2}' | cut -d'/' -f1)
    echo "$VM_NAME: $IP"
done

echo ""
echo "Next steps:"
echo "1. Generate Ansible inventory: cd ../terraform && terraform apply"
echo "2. Install K3s: cd ../ansible && ansible-playbook -i inventory.yml playbooks/k3s-install.yml"
```

### lima/scripts/destroy-vms.sh
```bash
#!/bin/bash
set -e

CONTROL_PLANE_COUNT=${1:-1}
WORKER_COUNT=${2:-2}

echo "Destroying K3s cluster VMs..."

# Stop and delete control plane nodes
for i in $(seq 1 $CONTROL_PLANE_COUNT); do
    VM_NAME="k3s-control-$i"
    echo "Deleting $VM_NAME..."
    limactl stop "$VM_NAME" 2>/dev/null || true
    limactl delete "$VM_NAME" 2>/dev/null || true
done

# Stop and delete worker nodes
for i in $(seq 1 $WORKER_COUNT); do
    VM_NAME="k3s-worker-$i"
    echo "Deleting $VM_NAME..."
    limactl stop "$VM_NAME" 2>/dev/null || true
    limactl delete "$VM_NAME" 2>/dev/null || true
done

echo "All VMs destroyed!"
limactl list
```

## Step 3: Terraform Configuration

### terraform/variables.tf
```hcl
variable "control_plane_count" {
  description = "Number of control plane nodes"
  default     = 1
}

variable "worker_count" {
  description = "Number of worker nodes"
  default     = 2
}
```

### terraform/main.tf
```hcl
terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

# Create VMs using Lima
resource "null_resource" "create_vms" {
  provisioner "local-exec" {
    command = "bash ${path.module}/../lima/scripts/create-vms.sh ${var.control_plane_count} ${var.worker_count}"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "bash ${path.module}/../lima/scripts/destroy-vms.sh ${var.control_plane_count} ${var.worker_count}"
  }
}

# Wait for VMs to be ready
resource "null_resource" "wait_for_vms" {
  provisioner "local-exec" {
    command = "sleep 20"
  }

  depends_on = [null_resource.create_vms]
}

# Get control plane IPs
data "external" "control_plane_ips" {
  count   = var.control_plane_count
  program = ["bash", "-c", "limactl shell k3s-control-${count.index + 1} ip -4 addr show lima0 | grep inet | awk '{print $2}' | cut -d'/' -f1 | jq -R '{ip: .}'"]
  
  depends_on = [null_resource.wait_for_vms]
}

# Get worker IPs
data "external" "worker_ips" {
  count   = var.worker_count
  program = ["bash", "-c", "limactl shell k3s-worker-${count.index + 1} ip -4 addr show lima0 | grep inet | awk '{print $2}' | cut -d'/' -f1 | jq -R '{ip: .}'"]
  
  depends_on = [null_resource.wait_for_vms]
}

# Generate Ansible inventory
resource "local_file" "ansible_inventory" {
  content = templatefile("${path.module}/inventory.tpl", {
    control_plane_ips = [for i in range(var.control_plane_count) : 
      data.external.control_plane_ips[i].result.ip]
    worker_ips = [for i in range(var.worker_count) : 
      data.external.worker_ips[i].result.ip]
  })
  filename = "${path.module}/../ansible/inventory.yml"

  depends_on = [
    data.external.control_plane_ips,
    data.external.worker_ips
  ]
}
```

### terraform/inventory.tpl
```yaml
all:
  children:
    control_plane:
      hosts:
%{ for ip in control_plane_ips ~}
        ${ip}:
%{ endfor ~}
    workers:
      hosts:
%{ for ip in worker_ips ~}
        ${ip}:
%{ endfor ~}
  vars:
    ansible_user: "${user}.linux"
    ansible_ssh_common_args: '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
    ansible_python_interpreter: /usr/bin/python3
```

### terraform/outputs.tf
```hcl
output "control_plane_ips" {
  value = [for i in range(var.control_plane_count) : 
    data.external.control_plane_ips[i].result.ip]
}

output "worker_ips" {
  value = [for i in range(var.worker_count) : 
    data.external.worker_ips[i].result.ip]
}

output "next_steps" {
  value = <<-EOT
  
  VMs created successfully!
  
  Control Plane IPs: ${join(", ", [for i in range(var.control_plane_count) : data.external.control_plane_ips[i].result.ip])}
  Worker IPs: ${join(", ", [for i in range(var.worker_count) : data.external.worker_ips[i].result.ip])}
  
  Next steps:
  1. Check VMs: limactl list
  2. Run Ansible: cd ../ansible && ansible-playbook -i inventory.yml playbooks/k3s-install.yml
  3. Get kubeconfig: limactl shell k3s-control-1 sudo cat /etc/rancher/k3s/k3s.yaml > ~/.kube/config
  4. Fix kubeconfig IP: sed -i '' 's/127.0.0.1/${data.external.control_plane_ips[0].result.ip}/g' ~/.kube/config
  5. Test: kubectl get nodes
  
  EOT
}
```

### terraform/terraform.tfvars
```hcl
control_plane_count = 1
worker_count        = 2
```

## Step 4: Ansible Configuration

### ansible/ansible.cfg
```ini
[defaults]
inventory = inventory.yml
host_key_checking = False
retry_files_enabled = False
timeout = 30

[ssh_connection]
pipelining = True
```

### ansible/playbooks/k3s-install.yml
```yaml
---
- name: Prepare all nodes
  hosts: all
  gather_facts: yes
  become: yes
  tasks:
    - name: Wait for system to be ready
      wait_for_connection:
        timeout: 60

    - name: Gather facts
      setup:

- name: Install K3s Control Plane
  hosts: control_plane
  become: yes
  tasks:
    - name: Install K3s on control plane
      shell: |
        curl -sfL https://get.k3s.io | sh -s - server \
          --write-kubeconfig-mode 644 \
          --disable traefik \
          --flannel-iface lima0 \
          --node-ip {{ ansible_facts['lima0']['ipv4']['address'] }} \
          --node-external-ip {{ ansible_facts['lima0']['ipv4']['address'] }} \
          --node-name {{ inventory_hostname }}
      args:
        creates: /usr/local/bin/k3s

    - name: Wait for K3s to be ready
      wait_for:
        path: /var/lib/rancher/k3s/server/node-token
        state: present
        timeout: 120

    - name: Get node token
      slurp:
        src: /var/lib/rancher/k3s/server/node-token
      register: node_token

    - name: Set control plane IP fact
      set_fact:
        control_plane_ip: "{{ ansible_facts['lima0']['ipv4']['address'] }}"

- name: Install K3s Workers
  hosts: workers
  become: yes
  tasks:
    - name: Install K3s agent
      shell: |
        curl -sfL https://get.k3s.io | K3S_URL=https://{{ hostvars[groups['control_plane'][0]]['control_plane_ip'] }}:6443 \
          K3S_TOKEN={{ hostvars[groups['control_plane'][0]]['node_token']['content'] | b64decode | trim }} \
          sh -s - agent \
          --flannel-iface lima0 \
          --node-ip {{ ansible_facts['lima0']['ipv4']['address'] }} \
          --node-external-ip {{ ansible_facts['lima0']['ipv4']['address'] }} \
          --node-name {{ inventory_hostname }}
      args:
        creates: /usr/local/bin/k3s

- name: Verify Cluster
  hosts: control_plane
  become: yes
  tasks:
    - name: Wait for nodes
      shell: kubectl get nodes --no-headers | grep " Ready" | wc -l
      register: ready_nodes
      until: ready_nodes.stdout | int == groups['all'] | length
      retries: 20
      delay: 10

    - name: Show cluster status
      shell: kubectl get nodes -o wide
      register: cluster_status

    - name: Display cluster
      debug:
        var: cluster_status.stdout_lines
```

### ansible/playbooks/k3s-reset.yml
```yaml
---
- name: Reset K3s Cluster
  hosts: all
  become: yes
  tasks:
    - name: Run K3s uninstall scripts
      shell: |
        if [ -f /usr/local/bin/k3s-killall.sh ]; then
          /usr/local/bin/k3s-killall.sh
        fi
        if [ -f /usr/local/bin/k3s-uninstall.sh ]; then
          /usr/local/bin/k3s-uninstall.sh
        fi
        if [ -f /usr/local/bin/k3s-agent-uninstall.sh ]; then
          /usr/local/bin/k3s-agent-uninstall.sh
        fi
      ignore_errors: yes

    - name: Remove K3s directories
      file:
        path: "{{ item }}"
        state: absent
      loop:
        - /etc/rancher
        - /var/lib/rancher
        - /var/lib/kubelet
```

## Step 5: Usage

### Initial Setup

```bash
# 1. Install prerequisites
brew install lima terraform ansible socket_vmnet
sudo brew services start socket_vmnet

# 2. Copy socket_vmnet binary to standard location
SOCKET_VERSION=$(ls /opt/homebrew/Cellar/socket_vmnet/ | head -1)
sudo mkdir -p /opt/socket_vmnet/bin
sudo cp /opt/homebrew/Cellar/socket_vmnet/$SOCKET_VERSION/bin/socket_vmnet /opt/socket_vmnet/bin/socket_vmnet

# 3. Configure sudoers for Lima
limactl sudoers > /tmp/etc_sudoers.d_lima
sudo install -o root /tmp/etc_sudoers.d_lima "/private/etc/sudoers.d/lima"

# 4. Make scripts executable
chmod +x lima/scripts/*.sh

# 5. Create VMs and generate inventory
cd terraform
terraform init
terraform apply

# 6. Install K3s cluster
cd ../ansible
ansible-playbook -i inventory.yml playbooks/k3s-install.yml

# 7. Get kubeconfig
CONTROL_IP=$(terraform output -json control_plane_ips | jq -r '.[0]')
limactl shell k3s-control-1 sudo cat /etc/rancher/k3s/k3s.yaml > ~/.kube/config
sed -i '' "s/127.0.0.1/$CONTROL_IP/g" ~/.kube/config

# 8. Verify
kubectl get nodes -o wide
```

### Common Operations

```bash
# List VMs
limactl list

# SSH into a VM
limactl shell k3s-control-1

# Stop all VMs
limactl stop k3s-control-1 k3s-worker-1 k3s-worker-2

# Start all VMs
limactl start k3s-control-1 k3s-worker-1 k3s-worker-2

# Get VM IP
limactl shell k3s-control-1 ip -4 addr show lima0 | grep inet

# Reset K3s (keep VMs)
cd ansible
ansible-playbook -i inventory.yml playbooks/k3s-reset.yml
ansible-playbook -i inventory.yml playbooks/k3s-install.yml

# Destroy everything
cd terraform
terraform destroy

# Or manually
bash lima/scripts/destroy-vms.sh 1 2
```

### Troubleshooting Networking

```bash
# Check if socket_vmnet is running
sudo brew services list | grep socket_vmnet

# Test VM connectivity
limactl shell k3s-control-1 ping -c 3 $(limactl shell k3s-worker-1 hostname -I | awk '{print $1}')

# Check network interface in VM
limactl shell k3s-control-1 ip addr show lima0

# View K3s logs
limactl shell k3s-control-1 sudo journalctl -u k3s -f

# Check firewall (if issues persist)
limactl shell k3s-control-1 sudo iptables -L -n -v
```

## Advantages of This Lima Setup

1. **Full control** - Customize every aspect of VMs via YAML
2. **Reproducible** - All configs in Git
3. **Proper networking** - socket_vmnet enables VM-to-VM communication
4. **Flexible** - Easy to change distros, resources, provisioning
5. **Transparent** - You can see exactly what Lima is doing

## Tips

1. Always use `lima0` interface for K3s (not `eth0`)
2. Keep MAC addresses unique per VM
3. socket_vmnet must be running before creating VMs
4. Use `--flannel-iface lima0` flag for K3s
5. Back up your kubeconfig before destroying

## Next Steps

- Extend monitoring with alert / recording rules & SLO dashboards
- Add dynamic storage (e.g., Longhorn) for PVC provisioning
- Implement GitOps (ArgoCD or Flux) for manifests & Helm releases
- Introduce secret management (Sealed Secrets / External Secrets)
- Harden Tunnel routing & add Zero Trust access policies
- Enhance Homepage with authenticated widgets (Prometheus, Grafana, Home Assistant APIs)