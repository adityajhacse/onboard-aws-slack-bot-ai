# Lambda Layer for shared code
data "archive_file" "lambda_layer" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/shared_layer"
  output_path = "${path.module}/lambda_layer.zip"
}

resource "aws_lambda_layer_version" "shared_layer" {
  filename            = data.archive_file.lambda_layer.output_path
  layer_name          = "${var.name_prefix}-shared-layer"
  compatible_runtimes = [var.lambda_runtime]
  source_code_hash    = data.archive_file.lambda_layer.output_base64sha256

  description = "Shared utilities for DET onboarding Lambda functions"
}

# CloudWatch Log Groups for Lambda Functions
resource "aws_cloudwatch_log_group" "validate_intake" {
  name              = "/aws/lambda/${var.name_prefix}-validate-intake"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "github_branch" {
  name              = "/aws/lambda/${var.name_prefix}-github-branch"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "github_commit" {
  name              = "/aws/lambda/${var.name_prefix}-github-commit"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "hcp_project" {
  name              = "/aws/lambda/${var.name_prefix}-hcp-project"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "hcp_workspace" {
  name              = "/aws/lambda/${var.name_prefix}-hcp-workspace"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "hcp_vars" {
  name              = "/aws/lambda/${var.name_prefix}-hcp-vars"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "status_tracker" {
  name              = "/aws/lambda/${var.name_prefix}-status-tracker"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "completion_notifier" {
  name              = "/aws/lambda/${var.name_prefix}-completion-notifier"
  retention_in_days = 14
}

# Lambda Function: Validate Intake
data "archive_file" "validate_intake" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/validate_intake"
  output_path = "${path.module}/validate_intake.zip"
}

resource "aws_lambda_function" "validate_intake" {
  filename         = data.archive_file.validate_intake.output_path
  function_name    = "${var.name_prefix}-validate-intake"
  role             = var.lambda_execution_role_arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.validate_intake.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = var.common_env_vars
  }

  depends_on = [aws_cloudwatch_log_group.validate_intake]
}

# Lambda Function: GitHub Branch
data "archive_file" "github_branch" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/github_branch"
  output_path = "${path.module}/github_branch.zip"
}

resource "aws_lambda_function" "github_branch" {
  filename         = data.archive_file.github_branch.output_path
  function_name    = "${var.name_prefix}-github-branch"
  role             = var.lambda_execution_role_arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.github_branch.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = var.common_env_vars
  }

  depends_on = [aws_cloudwatch_log_group.github_branch]
}

# Lambda Function: GitHub Commit
data "archive_file" "github_commit" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/github_commit"
  output_path = "${path.module}/github_commit.zip"
}

resource "aws_lambda_function" "github_commit" {
  filename         = data.archive_file.github_commit.output_path
  function_name    = "${var.name_prefix}-github-commit"
  role             = var.lambda_execution_role_arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.github_commit.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = var.common_env_vars
  }

  depends_on = [aws_cloudwatch_log_group.github_commit]
}

# Lambda Function: HCP Project
data "archive_file" "hcp_project" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/hcp_project"
  output_path = "${path.module}/hcp_project.zip"
}

resource "aws_lambda_function" "hcp_project" {
  filename         = data.archive_file.hcp_project.output_path
  function_name    = "${var.name_prefix}-hcp-project"
  role             = var.lambda_execution_role_arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.hcp_project.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = var.common_env_vars
  }

  depends_on = [aws_cloudwatch_log_group.hcp_project]
}

# Lambda Function: HCP Workspace
data "archive_file" "hcp_workspace" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/hcp_workspace"
  output_path = "${path.module}/hcp_workspace.zip"
}

resource "aws_lambda_function" "hcp_workspace" {
  filename         = data.archive_file.hcp_workspace.output_path
  function_name    = "${var.name_prefix}-hcp-workspace"
  role             = var.lambda_execution_role_arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.hcp_workspace.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = var.common_env_vars
  }

  depends_on = [aws_cloudwatch_log_group.hcp_workspace]
}

# Lambda Function: HCP Variables
data "archive_file" "hcp_vars" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/hcp_vars"
  output_path = "${path.module}/hcp_vars.zip"
}

resource "aws_lambda_function" "hcp_vars" {
  filename         = data.archive_file.hcp_vars.output_path
  function_name    = "${var.name_prefix}-hcp-vars"
  role             = var.lambda_execution_role_arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.hcp_vars.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = 30
  memory_size      = 256

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = var.common_env_vars
  }

  depends_on = [aws_cloudwatch_log_group.hcp_vars]
}

# Lambda Function: Status Tracker
data "archive_file" "status_tracker" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/status_tracker"
  output_path = "${path.module}/status_tracker.zip"
}

resource "aws_lambda_function" "status_tracker" {
  filename         = data.archive_file.status_tracker.output_path
  function_name    = "${var.name_prefix}-status-tracker"
  role             = var.lambda_execution_role_arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.status_tracker.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = 30
  memory_size      = 256

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = merge(
      var.common_env_vars,
      {
        DYNAMODB_LOGS_TABLE = var.execution_logs_table_name
      }
    )
  }

  depends_on = [aws_cloudwatch_log_group.status_tracker]
}

# Lambda Function: Completion Notifier
data "archive_file" "completion_notifier" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/completion_notifier"
  output_path = "${path.module}/completion_notifier.zip"
}

resource "aws_lambda_function" "completion_notifier" {
  filename         = data.archive_file.completion_notifier.output_path
  function_name    = "${var.name_prefix}-completion-notifier"
  role             = var.lambda_execution_role_arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.completion_notifier.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = 30
  memory_size      = 256

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = var.common_env_vars
  }

  depends_on = [aws_cloudwatch_log_group.completion_notifier]
}
