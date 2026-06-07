# Step Functions Architecture

## Overview

This document describes the refactored architecture that replaces the monolithic Python process with AWS Step Functions orchestrating independent Lambda functions.

## Architecture Components

### 1. API Gateway
- **Endpoint**: POST /onboard
- **Purpose**: Receives onboarding requests from Slack
- **Response**: Returns execution ARN for tracking
- **Integration**: Synchronously triggers Step Functions

### 2. Step Functions State Machine
Orchestrates the entire onboarding workflow with the following steps:

#### Step 1: Validate Intake
- **Lambda**: `validate_intake`
- **Input**: Raw intake data from Slack form
- **Output**: Validated and normalized intake data
- **Retry**: 2 attempts with exponential backoff
- **Error Handling**: Returns validation errors to Slack

#### Step 2: Create GitHub Branch
- **Lambda**: `github_branch`
- **Input**: Validated intake with project name
- **Output**: Branch name and status
- **Retry**: 3 attempts with exponential backoff
- **Error Handling**: Catches GitHubApiError, allows continuation if branch exists

#### Step 3: Commit to GitHub
- **Lambda**: `github_commit`
- **Input**: Validated intake + branch name
- **Output**: Commit SHA and file URL
- **Retry**: 3 attempts with exponential backoff
- **Error Handling**: Fails workflow if commit fails
- **Dependencies**: Requires Step 2 success

#### Step 4: Create HCP Terraform Project
- **Lambda**: `hcp_project`
- **Input**: Project name and slug
- **Output**: Project ID
- **Retry**: 3 attempts with exponential backoff
- **Error Handling**: Catches HcpTerraformError

#### Step 5: Create HCP Workspaces (Parallel)
- **Lambda**: `hcp_workspace`
- **Execution**: Parallel for each environment (Dev, QA, Prod)
- **Input**: Project ID, environment, workspace name, repo
- **Output**: Workspace ID and name per environment
- **Retry**: 3 attempts per workspace
- **Error Handling**: Individual workspace failures don't block others
- **Dependencies**: Requires Step 4 success

#### Step 6: Configure Workspace Variables (Parallel)
- **Lambda**: `hcp_vars`
- **Execution**: Parallel for each workspace created in Step 5
- **Input**: Workspace ID, environment
- **Output**: Configuration status
- **Retry**: 2 attempts per workspace
- **Dependencies**: Requires Step 5 success for that workspace

### 3. DynamoDB Table
- **Table Name**: `det-onboarding-executions`
- **Primary Key**: `execution_id` (String)
- **Attributes**:
  - `slack_channel`: Channel ID for status updates
  - `slack_user`: User ID who initiated
  - `status`: current, completed, failed
  - `current_step`: Step name being executed
  - `error_message`: Error details if failed
  - `intake_data`: Original request data
  - `created_at`: ISO timestamp
  - `updated_at`: ISO timestamp
  - `result`: Final output from Step Functions

### 4. Lambda Functions

All Lambda functions share common patterns:
- **Runtime**: Python 3.12
- **Layer**: Shared layer with common utilities
- **Logging**: CloudWatch Logs with structured JSON
- **Error Handling**: Custom exceptions with retry logic
- **Timeout**: 30-60 seconds per function
- **Memory**: 256-512 MB

### 5. Shared Lambda Layer
Contains reusable code:
- `github_api.py`: GitHub API interactions
- `hcp_terraform.py`: HCP Terraform API interactions
- `det_intake.py`: Validation and normalization logic
- Common utilities and dependencies

## Workflow State Machine Definition

```json
{
  "Comment": "DET Onboarding Workflow",
  "StartAt": "ValidateIntake",
  "States": {
    "ValidateIntake": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:validate_intake",
      "Retry": [{"ErrorEquals": ["States.ALL"], "MaxAttempts": 2}],
      "Next": "CreateGitHubBranch"
    },
    "CreateGitHubBranch": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:github_branch",
      "Retry": [{"ErrorEquals": ["States.ALL"], "MaxAttempts": 3}],
      "Next": "CommitToGitHub"
    },
    "CommitToGitHub": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:github_commit",
      "Retry": [{"ErrorEquals": ["States.ALL"], "MaxAttempts": 3}],
      "Next": "CreateHCPProject"
    },
    "CreateHCPProject": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:hcp_project",
      "Retry": [{"ErrorEquals": ["States.ALL"], "MaxAttempts": 3}],
      "Next": "CreateWorkspaces"
    },
    "CreateWorkspaces": {
      "Type": "Map",
      "ItemsPath": "$.environments",
      "MaxConcurrency": 3,
      "Iterator": {
        "StartAt": "CreateWorkspace",
        "States": {
          "CreateWorkspace": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:...:function:hcp_workspace",
            "Retry": [{"ErrorEquals": ["States.ALL"], "MaxAttempts": 3}],
            "End": true
          }
        }
      },
      "Next": "ConfigureVariables"
    },
    "ConfigureVariables": {
      "Type": "Map",
      "ItemsPath": "$.workspaces",
      "MaxConcurrency": 3,
      "Iterator": {
        "StartAt": "ConfigureVars",
        "States": {
          "ConfigureVars": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:...:function:hcp_vars",
            "Retry": [{"ErrorEquals": ["States.ALL"], "MaxAttempts": 2}],
            "End": true
          }
        }
      },
      "End": true
    }
  }
}
```

## Benefits of This Architecture

1. **Retry Logic**: Each step can be retried independently without restarting the entire workflow
2. **Parallel Execution**: Workspaces and their configurations are created concurrently
3. **Error Isolation**: Failure in one workspace doesn't affect others
4. **Observability**: CloudWatch provides detailed logs and metrics for each step
5. **Scalability**: Lambda auto-scales based on demand
6. **Maintainability**: Each Lambda function has a single responsibility
7. **Cost Efficiency**: Pay only for execution time, no idle resources
8. **Async Execution**: Slack receives immediate response, workflow runs in background

## Slack Integration Flow

1. User submits form in Slack → `/aws-det-poc` or `/aws-det-onboard`
2. Slack bot validates basic input
3. Bot calls API Gateway POST /onboard with intake data
4. API Gateway triggers Step Functions and returns execution ARN
5. Execution details saved to DynamoDB with Slack channel/user info
6. Slack displays "Processing..." message with execution ID
7. User can check status via `/aws-det-status <execution-id>`
8. Step Functions updates DynamoDB at each step
9. On completion/failure, Lambda sends final message to Slack channel
10. Slack displays final result with links to GitHub commit and HCP workspaces

## Environment Variables

Each Lambda function receives environment variables:
- `GITHUB_TOKEN`: GitHub API token
- `GITHUB_OWNER`: GitHub organization/user
- `HCP_TERRAFORM_TOKEN`: HCP Terraform API token
- `HCP_TERRAFORM_ORG`: HCP organization name
- `HCP_TERRAFORM_VCS_OAUTH_TOKEN_ID`: VCS OAuth token
- `HCP_TFC_AWS_RUN_ROLE_ARN`: AWS IAM role ARN for Terraform
- `DYNAMODB_TABLE`: Execution tracking table name
- `SLACK_BOT_TOKEN`: For sending status updates

## Deployment

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Plan infrastructure changes
terraform plan

# Apply infrastructure
terraform apply

# Package and deploy Lambda functions
./deploy_lambdas.sh
```
