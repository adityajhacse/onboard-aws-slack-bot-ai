variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

variable "executions_table_arn" {
  description = "ARN of the executions DynamoDB table"
  type        = string
}

variable "execution_logs_table_arn" {
  description = "ARN of the execution logs DynamoDB table"
  type        = string
}

variable "aws_region" {
  description = "AWS region for constructing ARN patterns"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID for constructing ARN patterns"
  type        = string
}
