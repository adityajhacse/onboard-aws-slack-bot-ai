# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region to deploy resources into."
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Deployment environment label (e.g. prod, staging, dev)."
  type        = string
  default     = "prod"
}

# ---------------------------------------------------------------------------
# VPC — set create_vpc=true to let Terraform build the network from scratch.
# When create_vpc=false you must supply vpc_id and subnet_ids below.
# ---------------------------------------------------------------------------

variable "create_vpc" {
  description = "Set to true to create a new VPC (and subnets) managed by this stack. When false, vpc_id and subnet_ids must be provided."
  type        = bool
  default     = true
}

variable "vpc_cidr" {
  description = "CIDR block for the new VPC. Only used when create_vpc=true."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets (one per AZ). Only used when create_vpc=true."
  type        = list(string)
  default     = ["10.0.0.0/24", "10.0.1.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the private subnets (one per AZ). Only used when create_vpc=true."
  type        = list(string)
  default     = ["10.0.2.0/24", "10.0.3.0/24"]
}

variable "vpc_id" {
  description = "ID of an existing VPC where the ECS service will run. Required when create_vpc=false."
  type        = string
  default     = null
}

variable "subnet_ids" {
  description = "List of existing subnet IDs for the ECS service (private subnets recommended). Required when create_vpc=false."
  type        = list(string)
  default     = null
}

variable "assign_public_ip" {
  description = "Whether to assign a public IP to the Fargate task. Set true only if subnets are public and there is no NAT gateway."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# ECS / Container
# ---------------------------------------------------------------------------

variable "ecr_image_uri" {
  description = "Full ECR image URI including tag."
  type        = string
  default     = "916657620953.dkr.ecr.us-west-2.amazonaws.com/ep-foundry-repo:latest"
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


