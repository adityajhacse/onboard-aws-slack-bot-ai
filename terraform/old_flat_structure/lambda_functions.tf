# CloudWatch Log Groups for Lambda Functions
resource "aws_cloudwatch_log_group" "validate_intake" {
  name              = "/aws/lambda/${local.name_prefix}-validate-intake"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "github_branch" {
  name              = "/aws/lambda/${local.name_prefix}-github-branch"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "github_commit" {
  name              = "/aws/lambda/${local.name_prefix}-github-commit"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "hcp_project" {
  name              = "/aws/lambda/${local.name_prefix}-hcp-project"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "hcp_workspace" {
  name              = "/aws/lambda/${local.name_prefix}-hcp-workspace"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "hcp_vars" {
  name              = "/aws/lambda/${local.name_prefix}-hcp-vars"
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
  function_name    = "${local.name_prefix}-validate-intake"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.validate_intake.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = local.common_env_vars
  }

  depends_on = [
    aws_cloudwatch_log_group.validate_intake,
    aws_iam_role_policy_attachment.lambda_basic
  ]
}

# Lambda Function: GitHub Branch
data "archive_file" "github_branch" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/github_branch"
  output_path = "${path.module}/github_branch.zip"
}

resource "aws_lambda_function" "github_branch" {
  filename         = data.archive_file.github_branch.output_path
  function_name    = "${local.name_prefix}-github-branch"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.github_branch.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = local.common_env_vars
  }

  depends_on = [
    aws_cloudwatch_log_group.github_branch,
    aws_iam_role_policy_attachment.lambda_basic
  ]
}

# Lambda Function: GitHub Commit
data "archive_file" "github_commit" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/github_commit"
  output_path = "${path.module}/github_commit.zip"
}

resource "aws_lambda_function" "github_commit" {
  filename         = data.archive_file.github_commit.output_path
  function_name    = "${local.name_prefix}-github-commit"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.github_commit.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = local.common_env_vars
  }

  depends_on = [
    aws_cloudwatch_log_group.github_commit,
    aws_iam_role_policy_attachment.lambda_basic
  ]
}

# Lambda Function: HCP Project
data "archive_file" "hcp_project" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/hcp_project"
  output_path = "${path.module}/hcp_project.zip"
}

resource "aws_lambda_function" "hcp_project" {
  filename         = data.archive_file.hcp_project.output_path
  function_name    = "${local.name_prefix}-hcp-project"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.hcp_project.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = local.common_env_vars
  }

  depends_on = [
    aws_cloudwatch_log_group.hcp_project,
    aws_iam_role_policy_attachment.lambda_basic
  ]
}

# Lambda Function: HCP Workspace
data "archive_file" "hcp_workspace" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/hcp_workspace"
  output_path = "${path.module}/hcp_workspace.zip"
}

resource "aws_lambda_function" "hcp_workspace" {
  filename         = data.archive_file.hcp_workspace.output_path
  function_name    = "${local.name_prefix}-hcp-workspace"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.hcp_workspace.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = local.common_env_vars
  }

  depends_on = [
    aws_cloudwatch_log_group.hcp_workspace,
    aws_iam_role_policy_attachment.lambda_basic
  ]
}

# Lambda Function: HCP Variables
data "archive_file" "hcp_vars" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/hcp_vars"
  output_path = "${path.module}/hcp_vars.zip"
}

resource "aws_lambda_function" "hcp_vars" {
  filename         = data.archive_file.hcp_vars.output_path
  function_name    = "${local.name_prefix}-hcp-vars"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.hcp_vars.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = 30
  memory_size      = 256

  layers = [aws_lambda_layer_version.shared_layer.arn]

  environment {
    variables = local.common_env_vars
  }

  depends_on = [
    aws_cloudwatch_log_group.hcp_vars,
    aws_iam_role_policy_attachment.lambda_basic
  ]
}
