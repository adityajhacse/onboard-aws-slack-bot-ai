# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/states/${local.name_prefix}-onboarding"
  retention_in_days = 14
}

# Step Functions State Machine
resource "aws_sfn_state_machine" "onboarding" {
  name     = "${local.name_prefix}-onboarding"
  role_arn = aws_iam_role.step_functions.arn

  definition = jsonencode({
    Comment = "DET Onboarding Workflow - Orchestrates intake validation, GitHub operations, and HCP Terraform provisioning"
    StartAt = "ValidateIntake"
    States = {
      ValidateIntake = {
        Type     = "Task"
        Resource = aws_lambda_function.validate_intake.arn
        Comment  = "Validate and normalize intake data from Slack form"
        Retry = [
          {
            ErrorEquals     = ["States.TaskFailed", "States.Timeout"]
            IntervalSeconds = 2
            MaxAttempts     = 2
            BackoffRate     = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.error"
            Next        = "ValidationFailed"
          }
        ]
        Next = "CheckValidation"
      }

      CheckValidation = {
        Type = "Choice"
        Comment = "Check if validation passed"
        Choices = [
          {
            Variable      = "$.valid"
            BooleanEquals = true
            Next          = "CreateGitHubBranch"
          }
        ]
        Default = "ValidationFailed"
      }

      ValidationFailed = {
        Type = "Fail"
        Error = "ValidationError"
        Cause = "Intake validation failed. Check missing_fields and errors in the output."
      }

      CreateGitHubBranch = {
        Type     = "Task"
        Resource = aws_lambda_function.github_branch.arn
        Comment  = "Create feature branch in GitHub repository"
        Retry = [
          {
            ErrorEquals     = ["States.TaskFailed", "States.Timeout"]
            IntervalSeconds = 3
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.error"
            Next        = "GitHubBranchFailed"
          }
        ]
        Next = "CommitToGitHub"
      }

      GitHubBranchFailed = {
        Type = "Fail"
        Error = "GitHubBranchError"
        Cause = "Failed to create GitHub branch after retries"
      }

      CommitToGitHub = {
        Type     = "Task"
        Resource = aws_lambda_function.github_commit.arn
        Comment  = "Commit intake JSON document to GitHub"
        Retry = [
          {
            ErrorEquals     = ["States.TaskFailed", "States.Timeout"]
            IntervalSeconds = 3
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.error"
            Next        = "GitHubCommitFailed"
          }
        ]
        Next = "CreateHCPProject"
      }

      GitHubCommitFailed = {
        Type = "Fail"
        Error = "GitHubCommitError"
        Cause = "Failed to commit to GitHub after retries"
      }

      CreateHCPProject = {
        Type     = "Task"
        Resource = aws_lambda_function.hcp_project.arn
        Comment  = "Create HCP Terraform project"
        Retry = [
          {
            ErrorEquals     = ["States.TaskFailed", "States.Timeout"]
            IntervalSeconds = 3
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.error"
            Next        = "HCPProjectFailed"
          }
        ]
        Next = "PrepareWorkspaceCreation"
      }

      HCPProjectFailed = {
        Type = "Fail"
        Error = "HCPProjectError"
        Cause = "Failed to create HCP Terraform project after retries"
      }

      PrepareWorkspaceCreation = {
        Type = "Pass"
        Comment = "Prepare data for parallel workspace creation"
        Parameters = {
          "project_id.$"       = "$.project_id"
          "project_name.$"     = "$.project_name"
          "project_slug.$"     = "$.intake.project_slug"
          "terraform_repo.$"   = "$.intake.terraform_repo"
          "workspace_names.$"  = "$.intake.workspace_names"
          "environments.$"     = "$.intake.environments"
          "slack_channel.$"    = "$.slack_channel"
          "slack_user.$"       = "$.slack_user"
          "execution_id.$"     = "$.execution_id"
          "file_url.$"         = "$.file_url"
          "branch_name.$"      = "$.branch_name"
        }
        Next = "CreateWorkspacesMap"
      }

      CreateWorkspacesMap = {
        Type         = "Map"
        ItemsPath    = "$.environments"
        MaxConcurrency = 3
        Comment      = "Create workspaces in parallel for each environment"
        Iterator = {
          StartAt = "CreateWorkspace"
          States = {
            CreateWorkspace = {
              Type     = "Task"
              Resource = aws_lambda_function.hcp_workspace.arn
              Parameters = {
                "environment.$"      = "$$.Map.Item.Value"
                "project_id.$"       = "$$.Execution.Input.project_id"
                "project_slug.$"     = "$$.Execution.Input.project_slug"
                "terraform_repo.$"   = "$$.Execution.Input.terraform_repo"
                "workspace_names.$"  = "$$.Execution.Input.workspace_names"
              }
              Retry = [
                {
                  ErrorEquals     = ["States.TaskFailed", "States.Timeout"]
                  IntervalSeconds = 3
                  MaxAttempts     = 3
                  BackoffRate     = 2.0
                }
              ]
              Catch = [
                {
                  ErrorEquals = ["States.ALL"]
                  ResultPath  = "$.error"
                  Next        = "WorkspaceCreationFailed"
                }
              ]
              End = true
            }
            WorkspaceCreationFailed = {
              Type = "Pass"
              Comment = "Mark workspace creation as failed but continue"
              Parameters = {
                "workspace_id"   = ""
                "workspace_name" = ""
                "environment.$"  = "$.environment"
                "error.$"        = "$.error"
                "failed"         = true
              }
              End = true
            }
          }
        }
        ResultPath = "$.workspaces"
        Next       = "ConfigureVariablesMap"
      }

      ConfigureVariablesMap = {
        Type           = "Map"
        ItemsPath      = "$.workspaces"
        MaxConcurrency = 3
        Comment        = "Configure environment variables for each workspace in parallel"
        Iterator = {
          StartAt = "CheckWorkspaceCreated"
          States = {
            CheckWorkspaceCreated = {
              Type = "Choice"
              Choices = [
                {
                  Variable      = "$.failed"
                  BooleanEquals = true
                  Next          = "SkipConfiguration"
                }
              ]
              Default = "ConfigureVars"
            }
            SkipConfiguration = {
              Type = "Pass"
              Comment = "Skip configuration for failed workspace"
              End = true
            }
            ConfigureVars = {
              Type     = "Task"
              Resource = aws_lambda_function.hcp_vars.arn
              Retry = [
                {
                  ErrorEquals     = ["States.TaskFailed", "States.Timeout"]
                  IntervalSeconds = 2
                  MaxAttempts     = 2
                  BackoffRate     = 2.0
                }
              ]
              Catch = [
                {
                  ErrorEquals = ["States.ALL"]
                  ResultPath  = "$.error"
                  Next        = "ConfigurationFailed"
                }
              ]
              End = true
            }
            ConfigurationFailed = {
              Type = "Pass"
              Comment = "Mark variable configuration as failed but continue"
              Parameters = {
                "workspace_id.$"   = "$.workspace_id"
                "workspace_name.$" = "$.workspace_name"
                "environment.$"    = "$.environment"
                "configured"       = false
                "error.$"          = "$.error"
              }
              End = true
            }
          }
        }
        ResultPath = "$.configured_workspaces"
        Next       = "Success"
      }

      Success = {
        Type = "Succeed"
        Comment = "Onboarding workflow completed successfully"
      }
    }
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  depends_on = [
    aws_iam_role_policy.step_functions_lambda,
    aws_iam_role_policy.step_functions_logs
  ]
}

# CloudWatch Alarms for Step Functions
resource "aws_cloudwatch_metric_alarm" "step_functions_failed_executions" {
  alarm_name          = "${local.name_prefix}-step-functions-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when Step Functions executions fail"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.onboarding.arn
  }
}

resource "aws_cloudwatch_metric_alarm" "step_functions_throttled_executions" {
  alarm_name          = "${local.name_prefix}-step-functions-throttled"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionThrottled"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "3"
  alarm_description   = "Alert when Step Functions executions are throttled"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.onboarding.arn
  }
}
