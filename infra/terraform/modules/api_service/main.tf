resource "aws_ecs_task_definition" "this" {
  family                   = "${var.project_name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = null
  task_role_arn            = null

  container_definitions = jsonencode([
    {
      name      = "afterhours-api"
      image     = var.container_image
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "DATABASE_URL", value = var.database_url },
        { name = "REDIS_URL", value = var.redis_url },
      ]
    }
  ])
}

resource "aws_ecs_service" "this" {
  name            = "${var.project_name}-api"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = true
  }
}
