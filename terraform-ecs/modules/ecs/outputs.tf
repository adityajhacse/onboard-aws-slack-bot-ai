output "cluster_name" {
  description = "Name of the ECS cluster."
  value       = aws_ecs_cluster.this.name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster."
  value       = aws_ecs_cluster.this.arn
}

output "service_name" {
  description = "Name of the ECS service."
  value       = aws_ecs_service.this.name
}

output "task_definition_arn" {
  description = "ARN of the latest active ECS task definition revision."
  value       = aws_ecs_task_definition.this.arn
}

output "log_group_name" {
  description = "CloudWatch log group name for the ECS service."
  value       = aws_cloudwatch_log_group.this.name
}

output "security_group_id" {
  description = "Security group ID attached to ECS Fargate tasks."
  value       = aws_security_group.task.id
}
