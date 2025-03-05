provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

resource "google_compute_instance" "agent_smith_vm" {
  name         = "agent-smith-${var.environment}"
  machine_type = var.machine_type
  
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 10
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${file(var.public_key_path)}"
  }
  
  metadata_startup_script = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y python3-pip python3-venv git
    pip3 install uv
  EOF

  tags = ["allow-ssh"]
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh-${var.environment}"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["allow-ssh"]
}