resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.project_name}-redis-subnets"
  subnet_ids = var.subnet_ids
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id       = "${var.project_name}-redis"
  description                = "Redis queue/cache for AfterHours"
  engine                     = "valkey"
  node_type                  = "cache.t4g.micro"
  num_cache_clusters         = 1
  automatic_failover_enabled = false
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = [var.app_security_group]
}
