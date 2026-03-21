output "cluster_arn" {
  value = aws_ecs_cluster.this.arn
}

output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.this.name
}
