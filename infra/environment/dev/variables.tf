variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "ssh_user" {
  description = "SSH username"
  type        = string
  default     = "gtaverne" 
}

variable "public_key_path" {
  description = "Path to public key file for SSH access"
  type        = string
  default     = "~/.ssh/github-actions-key.pub"
}