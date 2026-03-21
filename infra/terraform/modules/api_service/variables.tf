variable "project_name" {
  type = string
}

variable "cluster_arn" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "app_security_group_id" {
  type = string
}

variable "container_image" {
  type = string
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "redis_url" {
  type      = string
  sensitive = true
}
