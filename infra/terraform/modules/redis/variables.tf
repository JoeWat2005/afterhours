variable "project_name" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "app_security_group" {
  type = string
}
