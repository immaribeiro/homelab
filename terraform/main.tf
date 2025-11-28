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
