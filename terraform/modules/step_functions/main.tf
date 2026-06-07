# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/states/${var.name_prefix}-onboarding"
  retention_in_days = 14
}

# Step Functions State Machine with Status Tracking
resource "aws_sfn_state_machine" "onboarding" {
  name     = "${var.name_prefix}-onboarding"
  role_arn = var.step_functions_role_arn

  definition = templatefile("${path.module}/state_machine.json.tpl", {
    status_tracker_arn       = var.status_tracker_arn
    validate_intake_arn      = var.validate_intake_arn
    github_branch_arn        = var.github_branch_arn
    github_commit_arn        = var.github_commit_arn
    hcp_project_arn          = var.hcp_project_arn
    hcp_workspace_arn        = var.hcp_workspace_arn
    hcp_vars_arn             = var.hcp_vars_arn
    completion_notifier_arn  = var.completion_notifier_arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = var.tags
}
