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
