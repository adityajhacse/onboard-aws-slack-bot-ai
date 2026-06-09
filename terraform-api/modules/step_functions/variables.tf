variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

variable "step_functions_role_arn" {
  description = "ARN of the Step Functions execution role"
  type        = string
}

variable "validate_intake_arn" {
  description = "ARN of the validate intake Lambda function"
  type        = string
}

variable "github_branch_arn" {
  description = "ARN of the GitHub branch Lambda function"
  type        = string
}

variable "github_commit_arn" {
  description = "ARN of the GitHub commit Lambda function"
  type        = string
}

variable "hcp_project_arn" {
  description = "ARN of the HCP project Lambda function"
  type        = string
}

variable "hcp_workspace_arn" {
  description = "ARN of the HCP workspace Lambda function"
  type        = string
}

variable "hcp_vars_arn" {
  description = "ARN of the HCP vars Lambda function"
  type        = string
}

variable "status_tracker_arn" {
  description = "ARN of the status tracker Lambda function"
  type        = string
}

variable "completion_notifier_arn" {
  description = "ARN of the completion notifier Lambda function"
  type        = string
}
