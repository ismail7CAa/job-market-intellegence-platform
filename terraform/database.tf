# Secrets Manager for database password
resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.project_name}-db-password"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-db-secret"
  }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    engine   = "postgres"
    host     = aws_db_instance.main[0].endpoint
    port     = 5432
    dbname   = var.db_name
  })
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  count       = var.enable_rds ? 1 : 0
  name        = "${var.project_name}-rds-sg"
  description = "Security group for RDS"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  count      = var.enable_rds ? 1 : 0
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "main" {
  count                    = var.enable_rds ? 1 : 0
  identifier               = "${var.project_name}-postgres"
  engine                   = "postgres"
  engine_version           = "15.3"
  instance_class           = var.db_instance_class
  allocated_storage        = var.db_allocated_storage
  storage_type             = "gp3"
  storage_encrypted        = true
  db_name                  = var.db_name
  username                 = var.db_username
  password                 = var.db_password
  db_subnet_group_name     = aws_db_subnet_group.main[0].name
  vpc_security_group_ids   = [aws_security_group.rds[0].id]
  publicly_accessible      = false
  skip_final_snapshot      = var.environment != "prod"
  final_snapshot_identifier = var.environment != "prod" ? null : "${var.project_name}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  backup_retention_period  = var.environment == "prod" ? 30 : 7
  multi_az                 = var.environment == "prod" ? true : false
  deletion_protection      = var.environment == "prod" ? true : false

  performance_insights_enabled = var.environment == "prod" ? true : false

  tags = {
    Name = "${var.project_name}-postgres"
  }

  depends_on = [aws_db_subnet_group.main]
}

# ElastiCache Redis (optional)
resource "aws_elasticache_subnet_group" "main" {
  count      = var.enable_elasticache ? 1 : 0
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

resource "aws_security_group" "redis" {
  count       = var.enable_elasticache ? 1 : 0
  name        = "${var.project_name}-redis-sg"
  description = "Security group for Redis"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-redis-sg"
  }
}

resource "aws_elasticache_cluster" "main" {
  count              = var.enable_elasticache ? 1 : 0
  cluster_id         = "${var.project_name}-redis"
  engine             = "redis"
  node_type          = "cache.t3.micro"
  num_cache_nodes    = 1
  parameter_group_name = "default.redis7"
  engine_version     = "7.0"
  port               = 6379
  subnet_group_name  = aws_elasticache_subnet_group.main[0].name
  security_group_ids = [aws_security_group.redis[0].id]
  auto_failover_enabled = false

  tags = {
    Name = "${var.project_name}-redis"
  }
}
