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
