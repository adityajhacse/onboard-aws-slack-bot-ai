# API Gateway REST API
resource "aws_api_gateway_rest_api" "onboarding" {
  name        = "${var.name_prefix}-api"
  description = "API Gateway for DET onboarding workflow"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# API Gateway Resource: /onboard
resource "aws_api_gateway_resource" "onboard" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  parent_id   = aws_api_gateway_rest_api.onboarding.root_resource_id
  path_part   = "onboard"
}

# API Gateway Method: POST /onboard
resource "aws_api_gateway_method" "onboard_post" {
  rest_api_id   = aws_api_gateway_rest_api.onboarding.id
  resource_id   = aws_api_gateway_resource.onboard.id
  http_method   = "POST"
  authorization = "NONE"

  request_parameters = {
    "method.request.header.Content-Type" = true
  }
}

# API Gateway Integration with Step Functions
resource "aws_api_gateway_integration" "onboard_step_functions" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.onboard.id
  http_method = aws_api_gateway_method.onboard_post.http_method

  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = "arn:aws:apigateway:${var.region}:states:action/StartExecution"
  credentials             = var.api_gateway_role_arn

  request_templates = {
    "application/json" = jsonencode({
      stateMachineArn = var.state_machine_arn
      input           = "$util.escapeJavaScript($input.json('$'))"
    })
  }

  passthrough_behavior = "WHEN_NO_TEMPLATES"
}

# API Gateway Method Response
resource "aws_api_gateway_method_response" "onboard_200" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.onboard.id
  http_method = aws_api_gateway_method.onboard_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_method_response" "onboard_400" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.onboard.id
  http_method = aws_api_gateway_method.onboard_post.http_method
  status_code = "400"

  response_models = {
    "application/json" = "Error"
  }
}

resource "aws_api_gateway_method_response" "onboard_500" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.onboard.id
  http_method = aws_api_gateway_method.onboard_post.http_method
  status_code = "500"

  response_models = {
    "application/json" = "Error"
  }
}

# API Gateway Integration Response
resource "aws_api_gateway_integration_response" "onboard_200" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.onboard.id
  http_method = aws_api_gateway_method.onboard_post.http_method
  status_code = aws_api_gateway_method_response.onboard_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  response_templates = {
    "application/json" = jsonencode({
      executionArn = "$input.path('$.executionArn')"
      startDate    = "$input.path('$.startDate')"
      message      = "Onboarding workflow started successfully"
    })
  }

  depends_on = [aws_api_gateway_integration.onboard_step_functions]
}

resource "aws_api_gateway_integration_response" "onboard_400" {
  rest_api_id       = aws_api_gateway_rest_api.onboarding.id
  resource_id       = aws_api_gateway_resource.onboard.id
  http_method       = aws_api_gateway_method.onboard_post.http_method
  status_code       = aws_api_gateway_method_response.onboard_400.status_code
  selection_pattern = "4\\d{2}"

  response_templates = {
    "application/json" = jsonencode({
      error   = "Bad Request"
      message = "$input.path('$.message')"
    })
  }

  depends_on = [aws_api_gateway_integration.onboard_step_functions]
}

resource "aws_api_gateway_integration_response" "onboard_500" {
  rest_api_id       = aws_api_gateway_rest_api.onboarding.id
  resource_id       = aws_api_gateway_resource.onboard.id
  http_method       = aws_api_gateway_method.onboard_post.http_method
  status_code       = aws_api_gateway_method_response.onboard_500.status_code
  selection_pattern = "5\\d{2}"

  response_templates = {
    "application/json" = jsonencode({
      error   = "Internal Server Error"
      message = "Failed to start onboarding workflow"
    })
  }

  depends_on = [aws_api_gateway_integration.onboard_step_functions]
}

# API Gateway Resource: /status/{executionArn}
resource "aws_api_gateway_resource" "status" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  parent_id   = aws_api_gateway_rest_api.onboarding.root_resource_id
  path_part   = "status"
}

resource "aws_api_gateway_resource" "status_execution" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  parent_id   = aws_api_gateway_resource.status.id
  path_part   = "{executionArn+}"
}

# API Gateway Method: GET /status/{executionArn}
resource "aws_api_gateway_method" "status_get" {
  rest_api_id   = aws_api_gateway_rest_api.onboarding.id
  resource_id   = aws_api_gateway_resource.status_execution.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.path.executionArn" = true
  }
}

# API Gateway Integration for Status Check
resource "aws_api_gateway_integration" "status_step_functions" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.status_execution.id
  http_method = aws_api_gateway_method.status_get.http_method

  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = "arn:aws:apigateway:${var.region}:states:action/DescribeExecution"
  credentials             = var.api_gateway_role_arn

  request_templates = {
    "application/json" = jsonencode({
      executionArn = "$input.params('executionArn')"
    })
  }

  passthrough_behavior = "WHEN_NO_TEMPLATES"
}

# Status endpoint responses
resource "aws_api_gateway_method_response" "status_200" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.status_execution.id
  http_method = aws_api_gateway_method.status_get.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "status_200" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.status_execution.id
  http_method = aws_api_gateway_method.status_get.http_method
  status_code = aws_api_gateway_method_response.status_200.status_code

  response_templates = {
    "application/json" = "$input.json('$')"
  }

  depends_on = [aws_api_gateway_integration.status_step_functions]
}

# CORS Configuration for /onboard
resource "aws_api_gateway_method" "onboard_options" {
  rest_api_id   = aws_api_gateway_rest_api.onboarding.id
  resource_id   = aws_api_gateway_resource.onboard.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "onboard_options" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.onboard.id
  http_method = aws_api_gateway_method.onboard_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "onboard_options_200" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.onboard.id
  http_method = aws_api_gateway_method.onboard_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "onboard_options_200" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.onboard.id
  http_method = aws_api_gateway_method.onboard_options.http_method
  status_code = aws_api_gateway_method_response.onboard_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.onboard_options]
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "onboarding" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.onboard.id,
      aws_api_gateway_method.onboard_post.id,
      aws_api_gateway_integration.onboard_step_functions.id,
      aws_api_gateway_resource.status_execution.id,
      aws_api_gateway_method.status_get.id,
      aws_api_gateway_integration.status_step_functions.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.onboard_step_functions,
    aws_api_gateway_integration_response.onboard_200,
    aws_api_gateway_integration.status_step_functions,
    aws_api_gateway_integration_response.status_200,
  ]
}

# API Gateway Stage
resource "aws_api_gateway_stage" "onboarding" {
  deployment_id = aws_api_gateway_deployment.onboarding.id
  rest_api_id   = aws_api_gateway_rest_api.onboarding.id
  stage_name    = var.environment

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  xray_tracing_enabled = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-stage"
  })
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.name_prefix}"
  retention_in_days = 14
}

# API Gateway CloudWatch Role (account-wide setting)
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = var.api_gateway_cloudwatch_role_arn
}

# API Gateway Method Settings
resource "aws_api_gateway_method_settings" "onboarding" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  stage_name  = aws_api_gateway_stage.onboarding.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled    = true
    logging_level      = "INFO"
    data_trace_enabled = true
  }
}
