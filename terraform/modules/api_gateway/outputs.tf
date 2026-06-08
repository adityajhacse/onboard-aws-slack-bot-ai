output "api_id" {
  description = "ID of the API Gateway REST API"
  value       = aws_api_gateway_rest_api.onboarding.id
}

output "api_endpoint" {
  description = "Invoke URL of the API Gateway"
  value       = "${aws_api_gateway_stage.onboarding.invoke_url}/onboard"
}

output "status_endpoint" {
  description = "Status lookup endpoint URL"
  value       = "${aws_api_gateway_stage.onboarding.invoke_url}/status"
}

output "api_stage_name" {
  description = "Name of the API Gateway stage"
  value       = aws_api_gateway_stage.onboarding.stage_name
}

output "api_execution_arn" {
  description = "Execution ARN of the API Gateway"
  value       = aws_api_gateway_rest_api.onboarding.execution_arn
}
