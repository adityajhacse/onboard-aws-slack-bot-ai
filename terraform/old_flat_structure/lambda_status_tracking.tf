# CloudWatch Log Groups for Status Tracking Lambda Functions
resource "aws_cloudwatch_log_group" "status_tracker" {
  name              = "/aws/lambda/${local.name_prefix}-status-tracker"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "completion_notifier" {
  name              = "/aws/lambda/${local.name_prefix}-completion-notifier"
  retention_in_days = 14
}

# Lambda Function: Status Tracker
data "archive_file" "status_tracker" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/status_tracker"
  output_path = "${path.module}/status_tracker.zip"
}

resource "aws_lambda_function" "status_tracker" {
  filename         = data.archive_file.status_tracker.output_path
  function_name    = "${local.name_prefix}-status-tracker"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.status_tracker.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = 30
  memory_size      = 256

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = merge(
      local.common_env_vars,
      {
        DYNAMODB_LOGS_TABLE = aws_dynamodb_table.execution_logs.name
      }
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.status_tracker,
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy.lambda_dynamodb
  ]
}

# Lambda Function: Completion Notifier
data "archive_file" "completion_notifier" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/completion_notifier"
  output_path = "${path.module}/completion_notifier.zip"
}

resource "aws_lambda_function" "completion_notifier" {
  filename         = data.archive_file.completion_notifier.output_path
  function_name    = "${local.name_prefix}-completion-notifier"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.completion_notifier.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = 30
  memory_size      = 256

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = local.common_env_vars
  }

  depends_on = [
    aws_cloudwatch_log_group.completion_notifier,
    aws_iam_role_policy_attachment.lambda_basic
  ]
}

# Update IAM policy to include execution logs table
resource "aws_iam_role_policy" "lambda_execution_logs" {
  name   = "${local.name_prefix}-lambda-execution-logs"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_execution_logs.json
}

data "aws_iam_policy_document" "lambda_execution_logs" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.execution_logs.arn,
      "${aws_dynamodb_table.execution_logs.arn}/*"
    ]
  }
}
