# Add IAM policy for ECS task execution role to set secret
resource "aws_iam_role_policy" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-task-execution-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn
        ]
      }
    ]
  })
}

# Add policy for CloudWatch logs
resource "aws_iam_role_policy" "ecs_task_logs" {
  name = "${var.project_name}-ecs-task-logs-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.ecs.arn}:*"
        ]
      }
    ]
  })
}

# Outputs for CloudWatch Alarms
output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.ecs.name
}
