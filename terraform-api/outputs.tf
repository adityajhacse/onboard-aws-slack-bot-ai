# API Gateway Outputs
output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = module.api_gateway.api_endpoint
}

output "status_api_url" {
  description = "Status API endpoint URL (for Slack bot)"
  value       = module.api_gateway.status_endpoint
}

output "api_gateway_id" {
  description = "API Gateway REST API ID"
  value       = module.api_gateway.api_id
}

# Step Functions Outputs
output "state_machine_arn" {
  description = "Step Functions state machine ARN"
  value       = module.step_functions.state_machine_arn
}

output "state_machine_name" {
  description = "Step Functions state machine name"
  value       = module.step_functions.state_machine_name
}

# DynamoDB Outputs
output "dynamodb_executions_table_name" {
  description = "DynamoDB executions table name"
  value       = module.dynamodb.executions_table_name
}

output "dynamodb_execution_logs_table_name" {
  description = "DynamoDB execution logs table name"
  value       = module.dynamodb.execution_logs_table_name
}

# Lambda Outputs
output "lambda_function_arns" {
  description = "Map of Lambda function ARNs"
  value = {
    validate_intake      = module.lambda.validate_intake_function_arn
    github_branch        = module.lambda.github_branch_function_arn
    github_commit        = module.lambda.github_commit_function_arn
    hcp_project          = module.lambda.hcp_project_function_arn
    hcp_workspace        = module.lambda.hcp_workspace_function_arn
    hcp_vars             = module.lambda.hcp_vars_function_arn
    status_tracker       = module.lambda.status_tracker_function_arn
    completion_notifier  = module.lambda.completion_notifier_function_arn
    status_lookup        = module.lambda.status_lookup_function_arn
    validation_notifier  = module.lambda.validation_notifier_function_arn
  }
}

# IAM Outputs
output "lambda_execution_role_arn" {
  description = "Lambda execution role ARN"
  value       = module.iam.lambda_execution_role_arn
}

output "step_functions_execution_role_arn" {
  description = "Step Functions execution role ARN"
  value       = module.iam.step_functions_execution_role_arn
}
