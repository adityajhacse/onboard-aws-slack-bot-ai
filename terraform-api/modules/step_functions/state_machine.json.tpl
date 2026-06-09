{
  "Comment": "DET Onboarding Workflow with Status Tracking",
  "StartAt": "ValidateIntake",
  "States": {
    "ValidateIntake": {
      "Type": "Task",
      "Resource": "${validate_intake_arn}",
      "Comment": "Validate intake data (before creating any records)",
      "Retry": [{
        "ErrorEquals": ["States.TaskFailed", "States.Timeout"],
        "IntervalSeconds": 2,
        "MaxAttempts": 2,
        "BackoffRate": 2.0
      }],
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.lambda_error",
        "Next": "NotifyValidationFailure"
      }],
      "Next": "CheckValidation"
    },
    "CheckValidation": {
      "Type": "Choice",
      "Choices": [{
        "Variable": "$.valid",
        "BooleanEquals": true,
        "Next": "InitializeTracking"
      }],
      "Default": "NotifyValidationFailure"
    },
    "InitializeTracking": {
      "Type": "Task",
      "Resource": "${status_tracker_arn}",
      "Comment": "Create initial execution record (only after validation succeeds)",
      "Parameters": {
        "action": "start",
        "execution_id.$": "$$.Execution.Name",
        "intake.$": "$.intake",
        "slack_channel.$": "$.slack_channel",
        "slack_user.$": "$.slack_user"
      },
      "ResultPath": "$.tracking",
      "Next": "TrackValidationSuccess",
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.tracking_error",
        "Next": "TrackValidationSuccess"
      }]
    },
    "TrackValidationSuccess": {
      "Type": "Task",
      "Resource": "${status_tracker_arn}",
      "Parameters": {
        "action": "step_update",
        "execution_id.$": "$$.Execution.Name",
        "step_name": "ValidateIntake",
        "step_status": "SUCCEEDED",
        "result.$": "$.intake"
      },
      "ResultPath": null,
      "Next": "CreateGitHubBranch",
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "CreateGitHubBranch"}]
    },
    "NotifyValidationFailure": {
      "Type": "Task",
      "Resource": "${completion_notifier_arn}",
      "Parameters": {
        "execution_id.$": "$$.Execution.Name",
        "status": "FAILED",
        "slack_channel.$": "$.slack_channel",
        "slack_user.$": "$.slack_user",
        "project_name.$": "$.intake.project_name",
        "validation_errors.$": "$.errors"
      },
      "Next": "ValidationFailedEnd"
    },
    "ValidationFailedEnd": {
      "Type": "Fail",
      "Error": "ValidationFailed",
      "Cause": "Intake validation failed"
    },
    "CreateGitHubBranch": {
      "Type": "Task",
      "Resource": "${github_branch_arn}",
      "Parameters": {
        "intake.$": "$.intake",
        "slack_channel.$": "$.slack_channel",
        "slack_user.$": "$.slack_user",
        "execution_id.$": "$$.Execution.Name"
      },
      "Retry": [{
        "ErrorEquals": ["States.TaskFailed", "States.Timeout"],
        "IntervalSeconds": 3,
        "MaxAttempts": 3,
        "BackoffRate": 2.0
      }],
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.error",
        "Next": "NotifyFailure"
      }],
      "Next": "CommitToGitHub"
    },
    "CommitToGitHub": {
      "Type": "Task",
      "Resource": "${github_commit_arn}",
      "Parameters": {
        "intake.$": "$.intake",
        "branch_name.$": "$.branch_name",
        "slack_channel.$": "$.slack_channel",
        "slack_user.$": "$.slack_user",
        "execution_id.$": "$$.Execution.Name"
      },
      "Retry": [{
        "ErrorEquals": ["States.TaskFailed", "States.Timeout"],
        "IntervalSeconds": 3,
        "MaxAttempts": 3,
        "BackoffRate": 2.0
      }],
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.error",
        "Next": "NotifyFailure"
      }],
      "Next": "CreateHCPProject"
    },
    "CreateHCPProject": {
      "Type": "Task",
      "Resource": "${hcp_project_arn}",
      "Parameters": {
        "intake.$": "$.intake",
        "branch_name.$": "$.branch_name",
        "file_url.$": "$.file_url",
        "slack_channel.$": "$.slack_channel",
        "slack_user.$": "$.slack_user",
        "execution_id.$": "$$.Execution.Name"
      },
      "Retry": [{
        "ErrorEquals": ["States.TaskFailed", "States.Timeout"],
        "IntervalSeconds": 3,
        "MaxAttempts": 3,
        "BackoffRate": 2.0
      }],
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.error",
        "Next": "NotifyFailure"
      }],
      "Next": "PrepareWorkspaceCreation"
    },
    "PrepareWorkspaceCreation": {
      "Type": "Pass",
      "Parameters": {
        "project_id.$": "$.project_id",
        "project_name.$": "$.project_name",
        "project_slug.$": "$.intake.project_slug",
        "terraform_repo.$": "$.intake.terraform_repo",
        "workspace_names.$": "$.intake.workspace_names",
        "environments.$": "$.intake.environments",
        "slack_channel.$": "$.slack_channel",
        "slack_user.$": "$.slack_user",
        "branch_name.$": "$.branch_name"
      },
      "Next": "CreateWorkspacesMap"
    },
    "CreateWorkspacesMap": {
      "Type": "Map",
      "ItemsPath": "$.environments",
      "MaxConcurrency": 3,
      "Parameters": {
        "environment.$": "$$.Map.Item.Value",
        "project_id.$": "$.project_id",
        "project_slug.$": "$.project_slug",
        "terraform_repo.$": "$.terraform_repo",
        "workspace_names.$": "$.workspace_names",
        "execution_id.$": "$$.Execution.Name",
        "slack_channel.$": "$.slack_channel",
        "slack_user.$": "$.slack_user"
      },
      "Iterator": {
        "StartAt": "CreateWorkspace",
        "States": {
          "CreateWorkspace": {
            "Type": "Task",
            "Resource": "${hcp_workspace_arn}",
            "Retry": [{
              "ErrorEquals": ["States.TaskFailed"],
              "IntervalSeconds": 3,
              "MaxAttempts": 3,
              "BackoffRate": 2.0
            }],
            "End": true
          }
        }
      },
      "ResultPath": "$.workspaces",
      "Next": "TrackWorkspacesSuccess"
    },
    "TrackWorkspacesSuccess": {
      "Type": "Task",
      "Resource": "${status_tracker_arn}",
      "Parameters": {
        "action": "step_update",
        "execution_id.$": "$$.Execution.Name",
        "step_name": "CreateWorkspaces",
        "step_status": "SUCCEEDED",
        "result.$": "$.workspaces"
      },
      "ResultPath": null,
      "Next": "ConfigureVariablesMap",
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ConfigureVariablesMap"}]
    },
    "ConfigureVariablesMap": {
      "Type": "Map",
      "ItemsPath": "$.workspaces",
      "MaxConcurrency": 3,
      "Parameters": {
        "workspace.$": "$$.Map.Item.Value",
        "execution_id.$": "$$.Execution.Name",
        "slack_channel.$": "$.slack_channel",
        "slack_user.$": "$.slack_user"
      },
      "Iterator": {
        "StartAt": "ConfigureVars",
        "States": {
          "ConfigureVars": {
            "Type": "Task",
            "Resource": "${hcp_vars_arn}",
            "Retry": [{
              "ErrorEquals": ["States.TaskFailed"],
              "IntervalSeconds": 2,
              "MaxAttempts": 2,
              "BackoffRate": 2.0
            }],
            "End": true
          }
        }
      },
      "ResultPath": "$.configured_workspaces",
      "Next": "TrackVariablesSuccess"
    },
    "TrackVariablesSuccess": {
      "Type": "Task",
      "Resource": "${status_tracker_arn}",
      "Parameters": {
        "action": "step_update",
        "execution_id.$": "$$.Execution.Name",
        "step_name": "ConfigureVariables",
        "step_status": "SUCCEEDED",
        "result.$": "$.configured_workspaces"
      },
      "ResultPath": null,
      "Next": "TrackCompletion",
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "TrackCompletion"}]
    },
    "TrackCompletion": {
      "Type": "Task",
      "Resource": "${status_tracker_arn}",
      "Parameters": {
        "action": "complete",
        "execution_id.$": "$$.Execution.Name",
        "result.$": "$"
      },
      "ResultPath": null,
      "Next": "NotifySuccess",
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "NotifySuccess"}]
    },
    "NotifySuccess": {
      "Type": "Task",
      "Resource": "${completion_notifier_arn}",
      "Parameters": {
        "execution_id.$": "$$.Execution.Name",
        "status": "SUCCEEDED",
        "slack_channel.$": "$.slack_channel",
        "slack_user.$": "$.slack_user",
        "project_name.$": "$.project_name",
        "result.$": "$"
      },
      "End": true
    },
    "NotifyFailure": {
      "Type": "Task",
      "Resource": "${completion_notifier_arn}",
      "Parameters": {
        "execution_id.$": "$$.Execution.Name",
        "status": "FAILED",
        "slack_channel.$": "$.slack_channel",
        "slack_user.$": "$.slack_user",
        "error.$": "$.error"
      },
      "Next": "ExecutionFailed"
    },
    "ExecutionFailed": {
      "Type": "Fail",
      "Error": "WorkflowFailed",
      "Cause": "Onboarding workflow failed"
    }
  }
}
