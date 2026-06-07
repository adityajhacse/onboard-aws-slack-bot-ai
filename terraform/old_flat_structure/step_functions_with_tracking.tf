# Step Functions State Machine with Status Tracking
# This file replaces step_functions.tf with enhanced status tracking

resource "aws_sfn_state_machine" "onboarding_with_tracking" {
  name     = "${local.name_prefix}-onboarding-v2"
  role_arn = aws_iam_role.step_functions.arn

  definition = jsonencode({
    Comment = "DET Onboarding Workflow with Status Tracking and Notifications"
    StartAt = "InitializeTracking"
    States = {

      # Initialize execution tracking
      InitializeTracking = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Comment  = "Create initial execution record in DynamoDB"
        Parameters = {
          "action"          = "start"
          "execution_id.$"  = "$$.Execution.Name"
          "intake.$"        = "$.intake"
          "slack_channel.$" = "$.slack_channel"
          "slack_user.$"    = "$.slack_user"
        }
        ResultPath = "$.tracking"
        Next       = "ValidateIntake"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.tracking_error"
            Next        = "ValidateIntake"  # Continue even if tracking fails
          }
        ]
      }

      # Step 1: Validate Intake
      ValidateIntake = {
        Type     = "Task"
        Resource = aws_lambda_function.validate_intake.arn
        Comment  = "Validate and normalize intake data"
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
            Next        = "TrackValidationFailure"
          }
        ]
        Next = "TrackValidationSuccess"
      }

      TrackValidationSuccess = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "ValidateIntake"
          "step_status"    = "SUCCEEDED"
          "result.$"       = "$.intake"
        }
        ResultPath = null
        Next       = "CheckValidation"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "CheckValidation"
          }
        ]
      }

      TrackValidationFailure = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "ValidateIntake"
          "step_status"    = "FAILED"
          "error.$"        = "$.error.Cause"
        }
        ResultPath = null
        Next       = "ValidationFailed"
      }

      CheckValidation = {
        Type = "Choice"
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
        Type = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "fail"
          "execution_id.$" = "$$.Execution.Name"
          "error"          = "Intake validation failed"
        }
        ResultPath = null
        Next       = "NotifyFailure"
      }

      # Step 2: Create GitHub Branch
      CreateGitHubBranch = {
        Type     = "Task"
        Resource = aws_lambda_function.github_branch.arn
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
            Next        = "TrackGitHubBranchFailure"
          }
        ]
        Next = "TrackGitHubBranchSuccess"
      }

      TrackGitHubBranchSuccess = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "CreateGitHubBranch"
          "step_status"    = "SUCCEEDED"
          "result.$"       = "$.branch_name"
        }
        ResultPath = null
        Next       = "CommitToGitHub"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "CommitToGitHub"
          }
        ]
      }

      TrackGitHubBranchFailure = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "CreateGitHubBranch"
          "step_status"    = "FAILED"
          "error.$"        = "$.error.Cause"
        }
        ResultPath = null
        Next       = "GitHubBranchFailed"
      }

      GitHubBranchFailed = {
        Type = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "fail"
          "execution_id.$" = "$$.Execution.Name"
          "error"          = "Failed to create GitHub branch"
        }
        ResultPath = null
        Next       = "NotifyFailure"
      }

      # Step 3: Commit to GitHub
      CommitToGitHub = {
        Type     = "Task"
        Resource = aws_lambda_function.github_commit.arn
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
            Next        = "TrackGitHubCommitFailure"
          }
        ]
        Next = "TrackGitHubCommitSuccess"
      }

      TrackGitHubCommitSuccess = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "CommitToGitHub"
          "step_status"    = "SUCCEEDED"
          "result"         = {
            "file_url.$"   = "$.file_url"
            "commit_sha.$" = "$.commit_sha"
          }
        }
        ResultPath = null
        Next       = "CreateHCPProject"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "CreateHCPProject"
          }
        ]
      }

      TrackGitHubCommitFailure = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "CommitToGitHub"
          "step_status"    = "FAILED"
          "error.$"        = "$.error.Cause"
        }
        ResultPath = null
        Next       = "GitHubCommitFailed"
      }

      GitHubCommitFailed = {
        Type = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "fail"
          "execution_id.$" = "$$.Execution.Name"
          "error"          = "Failed to commit to GitHub"
        }
        ResultPath = null
        Next       = "NotifyFailure"
      }

      # Step 4: Create HCP Project
      CreateHCPProject = {
        Type     = "Task"
        Resource = aws_lambda_function.hcp_project.arn
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
            Next        = "TrackHCPProjectFailure"
          }
        ]
        Next = "TrackHCPProjectSuccess"
      }

      TrackHCPProjectSuccess = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "CreateHCPProject"
          "step_status"    = "SUCCEEDED"
          "result"         = {
            "project_id.$"   = "$.project_id"
            "project_name.$" = "$.project_name"
          }
        }
        ResultPath = null
        Next       = "PrepareWorkspaceCreation"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PrepareWorkspaceCreation"
          }
        ]
      }

      TrackHCPProjectFailure = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "CreateHCPProject"
          "step_status"    = "FAILED"
          "error.$"        = "$.error.Cause"
        }
        ResultPath = null
        Next       = "HCPProjectFailed"
      }

      HCPProjectFailed = {
        Type = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "fail"
          "execution_id.$" = "$$.Execution.Name"
          "error"          = "Failed to create HCP Terraform project"
        }
        ResultPath = null
        Next       = "NotifyFailure"
      }

      # Prepare for parallel workspace creation
      PrepareWorkspaceCreation = {
        Type = "Pass"
        Parameters = {
          "project_id.$"       = "$.project_id"
          "project_name.$"     = "$.project_name"
          "project_slug.$"     = "$.intake.project_slug"
          "terraform_repo.$"   = "$.intake.terraform_repo"
          "workspace_names.$"  = "$.intake.workspace_names"
          "environments.$"     = "$.intake.environments"
          "slack_channel.$"    = "$.slack_channel"
          "slack_user.$"       = "$.slack_user"
          "execution_id.$"     = "$$.Execution.Name"
          "file_url.$"         = "$.file_url"
          "branch_name.$"      = "$.branch_name"
        }
        Next = "TrackWorkspaceStart"
      }

      TrackWorkspaceStart = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "CreateWorkspaces"
          "step_status"    = "RUNNING"
        }
        ResultPath = null
        Next       = "CreateWorkspacesMap"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "CreateWorkspacesMap"
          }
        ]
      }

      # Parallel workspace creation
      CreateWorkspacesMap = {
        Type           = "Map"
        ItemsPath      = "$.environments"
        MaxConcurrency = 3
        Iterator = {
          StartAt = "CreateWorkspace"
          States = {
            CreateWorkspace = {
              Type     = "Task"
              Resource = aws_lambda_function.hcp_workspace.arn
              Parameters = {
                "environment.$"     = "$$.Map.Item.Value"
                "project_id.$"      = "$$.Execution.Input.project_id"
                "project_slug.$"    = "$$.Execution.Input.project_slug"
                "terraform_repo.$"  = "$$.Execution.Input.terraform_repo"
                "workspace_names.$" = "$$.Execution.Input.workspace_names"
              }
              Retry = [
                {
                  ErrorEquals     = ["States.TaskFailed"]
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
              Parameters = {
                "workspace_id"  = ""
                "workspace_name" = ""
                "environment.$" = "$.environment"
                "error.$"       = "$.error.Cause"
                "failed"        = true
              }
              End = true
            }
          }
        }
        ResultPath = "$.workspaces"
        Next       = "TrackWorkspaceComplete"
      }

      TrackWorkspaceComplete = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "CreateWorkspaces"
          "step_status"    = "SUCCEEDED"
          "result.$"       = "$.workspaces"
        }
        ResultPath = null
        Next       = "TrackVariablesStart"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "TrackVariablesStart"
          }
        ]
      }

      TrackVariablesStart = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "ConfigureVariables"
          "step_status"    = "RUNNING"
        }
        ResultPath = null
        Next       = "ConfigureVariablesMap"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "ConfigureVariablesMap"
          }
        ]
      }

      # Parallel variable configuration
      ConfigureVariablesMap = {
        Type           = "Map"
        ItemsPath      = "$.workspaces"
        MaxConcurrency = 3
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
              End  = true
            }
            ConfigureVars = {
              Type     = "Task"
              Resource = aws_lambda_function.hcp_vars.arn
              Retry = [
                {
                  ErrorEquals     = ["States.TaskFailed"]
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
              Parameters = {
                "workspace_id.$"   = "$.workspace_id"
                "workspace_name.$" = "$.workspace_name"
                "environment.$"    = "$.environment"
                "configured"       = false
                "error.$"          = "$.error.Cause"
              }
              End = true
            }
          }
        }
        ResultPath = "$.configured_workspaces"
        Next       = "TrackVariablesComplete"
      }

      TrackVariablesComplete = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "step_update"
          "execution_id.$" = "$$.Execution.Name"
          "step_name"      = "ConfigureVariables"
          "step_status"    = "SUCCEEDED"
          "result.$"       = "$.configured_workspaces"
        }
        ResultPath = null
        Next       = "TrackCompletion"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "TrackCompletion"
          }
        ]
      }

      # Mark execution as complete
      TrackCompletion = {
        Type     = "Task"
        Resource = aws_lambda_function.status_tracker.arn
        Parameters = {
          "action"         = "complete"
          "execution_id.$" = "$$.Execution.Name"
          "result.$"       = "$"
        }
        ResultPath = null
        Next       = "NotifySuccess"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "NotifySuccess"
          }
        ]
      }

      # Send success notification
      NotifySuccess = {
        Type     = "Task"
        Resource = aws_lambda_function.completion_notifier.arn
        Parameters = {
          "execution_id.$" = "$$.Execution.Name"
          "status"         = "SUCCEEDED"
          "slack_channel.$" = "$.slack_channel"
          "slack_user.$"   = "$.slack_user"
          "project_name.$" = "$.project_name"
          "result.$"       = "$"
        }
        End = true
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "Success"
          }
        ]
      }

      # Send failure notification
      NotifyFailure = {
        Type     = "Task"
        Resource = aws_lambda_function.completion_notifier.arn
        Parameters = {
          "execution_id.$"  = "$$.Execution.Name"
          "status"          = "FAILED"
          "slack_channel.$" = "$.slack_channel"
          "slack_user.$"    = "$.slack_user"
          "project_name.$"  = "$.intake.project_name"
          "error.$"         = "$.error"
        }
        Next = "ExecutionFailed"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "ExecutionFailed"
          }
        ]
      }

      Success = {
        Type = "Succeed"
      }

      ExecutionFailed = {
        Type = "Fail"
        Error = "WorkflowExecutionFailed"
        Cause = "One or more steps in the onboarding workflow failed"
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
    aws_iam_role_policy.step_functions_logs,
    aws_lambda_function.status_tracker,
    aws_lambda_function.completion_notifier
  ]
}
