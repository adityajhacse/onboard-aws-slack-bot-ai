variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

variable "lambda_runtime" {
  description = "Lambda runtime version"
  type        = string
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
}

variable "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution IAM role"
  type        = string
}

variable "common_env_vars" {
  description = "Common environment variables for Lambda functions"
  type        = map(string)
  sensitive   = true
}

variable "execution_logs_table_name" {
  description = "Name of the execution logs DynamoDB table"
  type        = string
}
