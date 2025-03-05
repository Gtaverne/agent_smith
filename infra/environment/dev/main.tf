module "vm" {
  source = "../../vm"
  
  project_id  = var.project_id
  region      = var.region
  zone        = var.zone
  environment = "dev"
  machine_type = "e2-micro"
}

output "vm_ip" {
  value = module.vm.instance_ip
}

output "vm_name" {
  value = module.vm.instance_name
}