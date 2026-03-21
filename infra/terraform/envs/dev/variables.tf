variable "aws_region" {
  description = "AWS region for the development stack."
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  description = "Name prefix applied across resources."
  type        = string
  default     = "afterhours"
}

variable "container_image_api" {
  description = "Container image URI for the API service."
  type        = string
  default     = "ghcr.io/algorithmavengers/afterhours-api:latest"
}

variable "container_image_worker" {
  description = "Container image URI for the worker service."
  type        = string
  default     = "ghcr.io/algorithmavengers/afterhours-worker:latest"
}
