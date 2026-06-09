output "validate_intake_function_arn" {
  description = "ARN of the validate intake Lambda function"
  value       = aws_lambda_function.validate_intake.arn
}

output "github_branch_function_arn" {
  description = "ARN of the GitHub branch Lambda function"
  value       = aws_lambda_function.github_branch.arn
}

output "github_commit_function_arn" {
  description = "ARN of the GitHub commit Lambda function"
  value       = aws_lambda_function.github_commit.arn
}

output "hcp_project_function_arn" {
  description = "ARN of the HCP project Lambda function"
  value       = aws_lambda_function.hcp_project.arn
}

output "hcp_workspace_function_arn" {
  description = "ARN of the HCP workspace Lambda function"
  value       = aws_lambda_function.hcp_workspace.arn
}

output "hcp_vars_function_arn" {
  description = "ARN of the HCP vars Lambda function"
  value       = aws_lambda_function.hcp_vars.arn
}

output "status_tracker_function_arn" {
  description = "ARN of the status tracker Lambda function"
  value       = aws_lambda_function.status_tracker.arn
}

output "completion_notifier_function_arn" {
  description = "ARN of the completion notifier Lambda function"
  value       = aws_lambda_function.completion_notifier.arn
}

output "status_lookup_function_arn" {
  description = "ARN of the status lookup Lambda function"
  value       = aws_lambda_function.status_lookup.arn
}

output "status_lookup_function_name" {
  description = "Name of the status lookup Lambda function"
  value       = aws_lambda_function.status_lookup.function_name
}

output "status_lookup_function_invoke_arn" {
  description = "Invoke ARN of the status lookup Lambda function"
  value       = aws_lambda_function.status_lookup.invoke_arn
}

output "validation_notifier_function_arn" {
  description = "ARN of the validation notifier Lambda function"
  value       = aws_lambda_function.validation_notifier.arn
}

output "all_lambda_function_arns" {
  description = "List of all Lambda function ARNs"
  value = [
    aws_lambda_function.validate_intake.arn,
    aws_lambda_function.github_branch.arn,
    aws_lambda_function.github_commit.arn,
    aws_lambda_function.hcp_project.arn,
    aws_lambda_function.hcp_workspace.arn,
    aws_lambda_function.hcp_vars.arn,
    aws_lambda_function.status_tracker.arn,
    aws_lambda_function.completion_notifier.arn,
    aws_lambda_function.status_lookup.arn,
    aws_lambda_function.validation_notifier.arn
  ]
}
