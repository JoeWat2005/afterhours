module "network" {
  source       = "../../modules/network"
  project_name = var.project_name
  aws_region   = var.aws_region
}

module "ecs_cluster" {
  source       = "../../modules/ecs_cluster"
  project_name = var.project_name
}

module "postgres" {
  source             = "../../modules/postgres"
  project_name       = var.project_name
  vpc_id             = module.network.vpc_id
  subnet_ids         = module.network.private_subnet_ids
  app_security_group = module.network.app_security_group_id
}

module "redis" {
  source             = "../../modules/redis"
  project_name       = var.project_name
  subnet_ids         = module.network.private_subnet_ids
  app_security_group = module.network.app_security_group_id
}

module "api_service" {
  source                = "../../modules/api_service"
  project_name          = var.project_name
  cluster_arn           = module.ecs_cluster.cluster_arn
  subnet_ids            = module.network.public_subnet_ids
  app_security_group_id = module.network.app_security_group_id
  container_image       = var.container_image_api
  database_url          = module.postgres.connection_url
  redis_url             = module.redis.redis_url
}

module "worker_service" {
  source                = "../../modules/worker_service"
  project_name          = var.project_name
  cluster_arn           = module.ecs_cluster.cluster_arn
  subnet_ids            = module.network.public_subnet_ids
  app_security_group_id = module.network.app_security_group_id
  container_image       = var.container_image_worker
  database_url          = module.postgres.connection_url
  redis_url             = module.redis.redis_url
}
