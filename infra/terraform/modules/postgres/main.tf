resource "aws_db_subnet_group" "this" {
  name       = "${var.project_name}-postgres-subnets"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "db" {
  name        = "${var.project_name}-postgres-sg"
  description = "Allow app access to PostgreSQL"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.app_security_group]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "this" {
  identifier             = "${var.project_name}-postgres"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "17.4"
  instance_class         = "db.t4g.micro"
  username               = "afterhours"
  password               = "change-me-in-secrets-manager"
  db_name                = "afterhours"
  skip_final_snapshot    = true
  publicly_accessible    = false
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
}
