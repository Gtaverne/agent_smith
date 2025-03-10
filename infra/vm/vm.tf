resource "google_artifact_registry_repository" "agent_smith" {
  project      = var.project_id
  location      = var.region
  repository_id = "agent-smith"
  description   = "Docker repository for Agent Smith"
  format        = "DOCKER"
}

# Create a service account for the VM
resource "google_service_account" "vm_service_account" {
  project      = var.project_id
  account_id   = "agent-smith-vm-sa"
  display_name = "Agent Smith VM Service Account"
}

# Grant Artifact Registry reader access
resource "google_artifact_registry_repository_iam_member" "vm_reader" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.agent_smith.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.vm_service_account.email}"
}

resource "google_compute_instance" "agent_smith_vm" {
  project      = var.project_id
  name         = "agent-smith-${var.environment}"
  machine_type = var.machine_type
  zone         = var.zone
  
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 15  # Reasonable size for Docker
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
    # Update and install dependencies
    apt-get update
    apt-get install -y \
      apt-transport-https \
      ca-certificates \
      curl \
      gnupg \
      lsb-release

    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Set up the Docker stable repository
    echo \
      "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io

    # Add current user to the docker group to avoid using sudo
    usermod -aG docker ${var.ssh_user}

    # Create directory for application data
    mkdir -p /opt/agent-smith/logs
    chmod -R 777 /opt/agent-smith/logs
  EOF

  service_account {
    email  = google_service_account.vm_service_account.email
    scopes = ["cloud-platform"]
  }

  tags = ["allow-ssh"]
}

resource "google_compute_firewall" "allow_ssh" {
  project = var.project_id
  name    = "allow-ssh-${var.environment}"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"] # SSH
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["allow-ssh"]
}