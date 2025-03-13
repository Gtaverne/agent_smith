variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "zone" {
  description = "GCP Zone"
  type        = string
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "machine_type" {
  description = "VM Machine Type"
  type        = string
  default     = "e2-small"
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