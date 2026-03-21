output "endpoint" {
  value = aws_db_instance.this.address
}

output "connection_url" {
  value     = "postgresql+psycopg://afterhours:change-me-in-secrets-manager@${aws_db_instance.this.address}:5432/afterhours"
  sensitive = true
}
