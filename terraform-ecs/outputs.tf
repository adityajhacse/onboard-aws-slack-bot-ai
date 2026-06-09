# ---------------------------------------------------------------------------
# VPC (only populated when create_vpc=true)
# ---------------------------------------------------------------------------

output "vpc_id" {
  description = "ID of the VPC used by the ECS service (module-created or pre-existing)."
  value       = local.resolved_vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs used by ECS tasks (module-created or pre-existing)."
  value       = local.resolved_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs (only set when create_vpc=true)."
  value       = var.create_vpc ? module.vpc[0].public_subnet_ids : []
}

# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------

output "secret_arn" {
  description = "ARN of the Secrets Manager secret holding all app credentials."
  value       = module.secrets.secret_arn
}

output "secret_name" {
  description = "Name of the Secrets Manager secret."
  value       = module.secrets.secret_name
}

# ---------------------------------------------------------------------------
# IAM
# ---------------------------------------------------------------------------

output "execution_role_arn" {
  description = "ARN of the ECS task execution IAM role."
  value       = module.iam.execution_role_arn
}

output "task_role_arn" {
  description = "ARN of the ECS task IAM role (used by the application container)."
  value       = module.iam.task_role_arn
}

# ---------------------------------------------------------------------------
# ECS
# ---------------------------------------------------------------------------

output "ecs_cluster_name" {
  description = "Name of the ECS cluster."
  value       = module.ecs.cluster_name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster."
  value       = module.ecs.cluster_arn
}

output "ecs_service_name" {
  description = "Name of the ECS service."
  value       = module.ecs.service_name
}

output "task_definition_arn" {
  description = "ARN of the latest active ECS task definition revision."
  value       = module.ecs.task_definition_arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name for the ECS service."
  value       = module.ecs.log_group_name
}

output "ecs_security_group_id" {
  description = "Security group ID attached to ECS Fargate tasks."
  value       = module.ecs.security_group_id
}
