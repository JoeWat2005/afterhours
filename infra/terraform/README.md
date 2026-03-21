# Terraform Layout

This is a scaffold, not a one-click production deployment. The point is to give
the team a clean place to grow the AWS infrastructure without mixing it into app
code.

## Structure

- `envs/dev`: composition layer for the development stack
- `modules/network`: VPC, subnets, and app-facing security groups
- `modules/ecs_cluster`: ECS/Fargate cluster and shared logging config
- `modules/api_service`: API task/service shape
- `modules/worker_service`: async worker task/service shape
- `modules/postgres`: RDS PostgreSQL/PostGIS-ready instance contract
- `modules/redis`: ElastiCache/Valkey Redis replication group contract

## What is intentionally missing

- production secrets handling
- CI/CD wiring
- Route53 / ACM / ALB listener rules
- NAT gateways and full private-subnet egress decisions

Those decisions depend on budget, AWS account shape, and how far the uni project
needs to go.
