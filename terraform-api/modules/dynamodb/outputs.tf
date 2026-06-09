output "executions_table_name" {
  description = "Name of the executions DynamoDB table"
  value       = aws_dynamodb_table.executions.name
}

output "executions_table_arn" {
  description = "ARN of the executions DynamoDB table"
  value       = aws_dynamodb_table.executions.arn
}

output "execution_logs_table_name" {
  description = "Name of the execution logs DynamoDB table"
  value       = aws_dynamodb_table.execution_logs.name
}

output "execution_logs_table_arn" {
  description = "ARN of the execution logs DynamoDB table"
  value       = aws_dynamodb_table.execution_logs.arn
}
