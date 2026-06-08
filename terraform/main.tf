terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.tags
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local variables
locals {
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name
  name_prefix = "${var.project_name}-${var.environment}"

  common_env_vars = {
    GITHUB_TOKEN                             = var.github_token
    GITHUB_OWNER                             = var.github_owner
    GITHUB_REPO                              = var.github_repo
    GITHUB_BASE_BRANCH                       = var.github_base_branch
    HCP_TERRAFORM_TOKEN                      = var.hcp_terraform_token
    HCP_TERRAFORM_ORG                        = var.hcp_terraform_org
    HCP_TERRAFORM_URL                        = var.hcp_terraform_url
    HCP_TERRAFORM_VCS_OAUTH_TOKEN_ID         = var.hcp_terraform_vcs_oauth_token_id
    HCP_TERRAFORM_GITHUB_APP_INSTALLATION_ID = var.hcp_terraform_github_app_installation_id
    HCP_TFC_AWS_RUN_ROLE_ARN                 = var.hcp_tfc_aws_run_role_arn
    DYNAMODB_TABLE                           = module.dynamodb.executions_table_name
    SLACK_BOT_TOKEN                          = var.slack_bot_token
  }
}

# DynamoDB Module
module "dynamodb" {
  source = "./modules/dynamodb"

  name_prefix = local.name_prefix
  tags        = var.tags
}

# IAM Module
# lambda_function_arns and state_machine_arn removed to break dependency cycle;
# IAM policies use predictable ARN patterns (name_prefix wildcard) instead.
module "iam" {
  source = "./modules/iam"

  name_prefix              = local.name_prefix
  tags                     = var.tags
  executions_table_arn     = module.dynamodb.executions_table_arn
  execution_logs_table_arn = module.dynamodb.execution_logs_table_arn
  aws_region               = local.region
  aws_account_id           = local.account_id
}

# Lambda Module
module "lambda" {
  source = "./modules/lambda"

  name_prefix               = local.name_prefix
  tags                      = var.tags
  lambda_runtime            = var.lambda_runtime
  lambda_memory_size        = var.lambda_memory_size
  lambda_timeout            = var.lambda_timeout
  lambda_execution_role_arn = module.iam.lambda_execution_role_arn
  common_env_vars           = local.common_env_vars
  execution_logs_table_name = module.dynamodb.execution_logs_table_name

  depends_on = [module.iam]
}

# Step Functions Module
module "step_functions" {
  source = "./modules/step_functions"

  name_prefix             = local.name_prefix
  tags                    = var.tags
  step_functions_role_arn = module.iam.step_functions_execution_role_arn
  validate_intake_arn     = module.lambda.validate_intake_function_arn
  github_branch_arn       = module.lambda.github_branch_function_arn
  github_commit_arn       = module.lambda.github_commit_function_arn
  hcp_project_arn         = module.lambda.hcp_project_function_arn
  hcp_workspace_arn       = module.lambda.hcp_workspace_function_arn
  hcp_vars_arn            = module.lambda.hcp_vars_function_arn
  status_tracker_arn      = module.lambda.status_tracker_function_arn
  completion_notifier_arn = module.lambda.completion_notifier_function_arn

  depends_on = [module.iam, module.lambda]
}

# API Gateway Module
module "api_gateway" {
  source = "./modules/api_gateway"

  name_prefix                     = local.name_prefix
  environment                     = var.environment
  region                          = local.region
  tags                            = var.tags
  state_machine_arn               = module.step_functions.state_machine_arn
  api_gateway_role_arn            = module.iam.api_gateway_step_functions_role_arn
  api_gateway_cloudwatch_role_arn = module.iam.api_gateway_cloudwatch_role_arn
  status_lookup_lambda_invoke_arn = module.lambda.status_lookup_function_invoke_arn
  status_lookup_lambda_name       = module.lambda.status_lookup_function_name

  depends_on = [module.step_functions, module.lambda]
}
