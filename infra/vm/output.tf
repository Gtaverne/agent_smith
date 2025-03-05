output "instance_ip" {
  description = "The public IP address of the VM instance"
  value       = google_compute_instance.agent_smith_vm.network_interface[0].access_config[0].nat_ip
}

output "instance_name" {
  description = "The name of the VM instance"
  value       = google_compute_instance.agent_smith_vm.name
}