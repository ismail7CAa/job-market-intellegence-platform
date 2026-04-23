variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "jmip"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "job-market-platform"
}

variable "container_image" {
  description = "Docker image URI"
  type        = string
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 8000
}

variable "task_cpu" {
  description = "ECS task CPU units"
  type        = string
  default     = "256"
}

variable "task_memory" {
  description = "ECS task memory in MB"
  type        = string
  default     = "512"
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 2
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "jobmarket"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

variable "enable_rds" {
  description = "Enable RDS database"
  type        = bool
  default     = true
}

variable "enable_elasticache" {
  description = "Enable ElastiCache Redis"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}
