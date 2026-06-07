# Lambda Layer for shared code
data "archive_file" "lambda_layer" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/shared_layer"
  output_path = "${path.module}/lambda_layer.zip"
}

resource "aws_lambda_layer_version" "shared_layer" {
  filename            = data.archive_file.lambda_layer.output_path
  layer_name          = "${local.name_prefix}-shared-layer"
  compatible_runtimes = [var.lambda_runtime]
  source_code_hash    = data.archive_file.lambda_layer.output_base64sha256

  description = "Shared utilities for DET onboarding Lambda functions"
}
