# ---------------------------------------------------------------------------
# Identity / naming
# ---------------------------------------------------------------------------

variable "project" {
  description = "Project name used to namespace all resource names."
  type        = string
}

variable "service_name" {
  description = "ECS service and container name."
  type        = string
}

variable "aws_region" {
  description = "AWS region where resources are deployed."
  type        = string
}

# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------

variable "vpc_id" {
  description = "ID of the VPC where the ECS service will run."
  type        = string
}

variable "subnet_ids" {
  description = "Unused — subnets are now discovered via data.aws_subnets.private (tag:project=ep-foundry, tag:Tier=private). Kept for interface compatibility."
  type        = list(string)
  default     = []
}

variable "assign_public_ip" {
  description = "Whether to assign a public IP to the Fargate task."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------

variable "ecr_image_uri" {
  description = "Full ECR image URI including tag."
  type        = string
}

variable "task_cpu" {
  description = "Fargate task CPU units (256 | 512 | 1024 | 2048 | 4096)."
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Number of ECS task replicas to run."
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "CloudWatch log group retention in days."
  type        = number
  default     = 30
}

# ---------------------------------------------------------------------------
# IAM — passed in from the iam module
# ---------------------------------------------------------------------------

variable "execution_role_arn" {
  description = "ARN of the ECS task execution IAM role."
  type        = string
}

variable "task_role_arn" {
  description = "ARN of the ECS task IAM role."
  type        = string
}

# ---------------------------------------------------------------------------
# Secrets — passed in from the secrets module
# ---------------------------------------------------------------------------

variable "secret_arn" {
  description = "ARN of the Secrets Manager secret; used to build valueFrom references."
  type        = string
}

