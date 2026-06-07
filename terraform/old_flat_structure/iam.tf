# IAM Role for Lambda Functions
resource "aws_iam_role" "lambda_execution" {
  name               = "${local.name_prefix}-lambda-execution"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

# Lambda Basic Execution Policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda DynamoDB Access Policy
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name   = "${local.name_prefix}-lambda-dynamodb"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_dynamodb.json
}

data "aws_iam_policy_document" "lambda_dynamodb" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:Scan"
    ]
    resources = [
      aws_dynamodb_table.executions.arn,
      "${aws_dynamodb_table.executions.arn}/*"
    ]
  }
}

# IAM Role for Step Functions
resource "aws_iam_role" "step_functions" {
  name               = "${local.name_prefix}-step-functions"
  assume_role_policy = data.aws_iam_policy_document.step_functions_assume_role.json
}

data "aws_iam_policy_document" "step_functions_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

# Step Functions Lambda Invocation Policy
resource "aws_iam_role_policy" "step_functions_lambda" {
  name   = "${local.name_prefix}-step-functions-lambda"
  role   = aws_iam_role.step_functions.id
  policy = data.aws_iam_policy_document.step_functions_lambda.json
}

data "aws_iam_policy_document" "step_functions_lambda" {
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = [
      aws_lambda_function.validate_intake.arn,
      aws_lambda_function.github_branch.arn,
      aws_lambda_function.github_commit.arn,
      aws_lambda_function.hcp_project.arn,
      aws_lambda_function.hcp_workspace.arn,
      aws_lambda_function.hcp_vars.arn,
      aws_lambda_function.status_tracker.arn,
      aws_lambda_function.completion_notifier.arn
    ]
  }
}

# Step Functions CloudWatch Logs Policy
resource "aws_iam_role_policy" "step_functions_logs" {
  name   = "${local.name_prefix}-step-functions-logs"
  role   = aws_iam_role.step_functions.id
  policy = data.aws_iam_policy_document.step_functions_logs.json
}

data "aws_iam_policy_document" "step_functions_logs" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups"
    ]
    resources = ["*"]
  }
}

# IAM Role for API Gateway
resource "aws_iam_role" "api_gateway" {
  name               = "${local.name_prefix}-api-gateway"
  assume_role_policy = data.aws_iam_policy_document.api_gateway_assume_role.json
}

data "aws_iam_policy_document" "api_gateway_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

# API Gateway Step Functions Invocation Policy
resource "aws_iam_role_policy" "api_gateway_step_functions" {
  name   = "${local.name_prefix}-api-gateway-step-functions"
  role   = aws_iam_role.api_gateway.id
  policy = data.aws_iam_policy_document.api_gateway_step_functions.json
}

data "aws_iam_policy_document" "api_gateway_step_functions" {
  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution"
    ]
    resources = [
      aws_sfn_state_machine.onboarding.arn
    ]
  }
}

# API Gateway CloudWatch Logs Policy
resource "aws_iam_role_policy_attachment" "api_gateway_logs" {
  role       = aws_iam_role.api_gateway.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}
