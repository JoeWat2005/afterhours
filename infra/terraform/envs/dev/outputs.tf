output "cluster_name" {
  value = module.ecs_cluster.cluster_name
}

output "api_service_name" {
  value = module.api_service.service_name
}

output "worker_service_name" {
  value = module.worker_service.service_name
}

output "database_endpoint" {
  value = module.postgres.endpoint
}

output "redis_endpoint" {
  value = module.redis.endpoint
}
