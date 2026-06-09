variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

variable "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  type        = string
}

variable "api_gateway_role_arn" {
  description = "ARN of the IAM role for API Gateway to invoke Step Functions"
  type        = string
}

variable "api_gateway_cloudwatch_role_arn" {
  description = "ARN of the IAM role for API Gateway account-wide CloudWatch logging"
  type        = string
}

variable "status_lookup_lambda_invoke_arn" {
  description = "Invoke ARN of the status lookup Lambda function"
  type        = string
}

variable "status_lookup_lambda_name" {
  description = "Name of the status lookup Lambda function"
  type        = string
}
