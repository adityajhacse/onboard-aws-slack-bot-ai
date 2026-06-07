variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "det-onboarding"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "github_token" {
  description = "GitHub personal access token"
  type        = string
  sensitive   = true
}

variable "github_owner" {
  description = "GitHub organization or user"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "github_base_branch" {
  description = "GitHub base branch for creating feature branches"
  type        = string
  default     = "main"
}

variable "hcp_terraform_token" {
  description = "HCP Terraform API token"
  type        = string
  sensitive   = true
}

variable "hcp_terraform_org" {
  description = "HCP Terraform organization name"
  type        = string
}

variable "hcp_terraform_url" {
  description = "HCP Terraform API URL"
  type        = string
  default     = "https://app.terraform.io"
}

variable "hcp_terraform_vcs_oauth_token_id" {
  description = "HCP Terraform VCS OAuth token ID"
  type        = string
  default     = ""
}

variable "hcp_terraform_github_app_installation_id" {
  description = "HCP Terraform GitHub App installation ID"
  type        = string
  default     = ""
}

variable "hcp_tfc_aws_run_role_arn" {
  description = "AWS IAM role ARN for HCP Terraform runs"
  type        = string
}

variable "slack_bot_token" {
  description = "Slack bot token for sending notifications"
  type        = string
  sensitive   = true
}

variable "lambda_runtime" {
  description = "Lambda runtime version"
  type        = string
  default     = "python3.12"
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    ManagedBy = "Terraform"
    Project   = "DET-Onboarding"
  }
}
