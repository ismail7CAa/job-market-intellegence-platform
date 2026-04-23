output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.main.arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.main.name
}

output "rds_endpoint" {
  description = "RDS database endpoint"
  value       = var.enable_rds ? aws_db_instance.main[0].endpoint : "Not enabled"
}

output "rds_address" {
  description = "RDS database address"
  value       = var.enable_rds ? aws_db_instance.main[0].address : "Not enabled"
}

output "database_password_secret_arn" {
  description = "ARN of the database password secret"
  value       = aws_secretsmanager_secret.db_password.arn
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = var.enable_elasticache ? aws_elasticache_cluster.main[0].cache_nodes[0].address : "Not enabled"
}

output "redis_port" {
  description = "Redis cluster port"
  value       = var.enable_elasticache ? aws_elasticache_cluster.main[0].port : "Not enabled"
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}
