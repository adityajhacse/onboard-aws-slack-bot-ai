# Architecture - System Design and Flow

Complete technical architecture for the AWS DET Onboarding Bot.

---

## System Overview

The system uses **serverless architecture** to automate infrastructure onboarding through Slack, orchestrating GitHub and HCP Terraform operations via AWS Step Functions and Lambda.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         USER LAYER                           │
│                                                              │
│  ┌──────────┐              ┌──────────┐                     │
│  │  Slack   │              │  Slack   │                     │
│  │  User    │─────────────▶│   Bot    │                     │
│  │          │ /aws-det-poc │          │                     │
│  └──────────┘   or chat    └────┬─────┘                     │
│                                  │                           │
└──────────────────────────────────┼───────────────────────────┘
                                   │
                                   │ HTTP POST
                                   ▼
┌─────────────────────────────────────────────────────────────┐
│                     AWS ENTRY LAYER                          │
│                                                              │
│                 ┌─────────────────┐                         │
│                 │  API Gateway    │                         │
│                 │  REST API       │                         │
│                 │  /onboard       │                         │
│                 └────────┬────────┘                         │
│                          │                                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           │ Trigger
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  ORCHESTRATION LAYER                         │
│                                                              │
│            ┌───────────────────────────┐                    │
│            │   Step Functions          │                    │
│            │   State Machine           │                    │
│            │   (6-step workflow)       │                    │
│            └──────────┬────────────────┘                    │
│                       │                                     │
└───────────────────────┼─────────────────────────────────────┘
                        │
                        │ Invokes
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXECUTION LAYER                           │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Lambda 1 │  │ Lambda 2 │  │ Lambda 3 │  │ Lambda 4 │   │
│  │ Validate │  │ GitHub   │  │ HCP      │  │ Notify   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│             ┌─────────────────────────┐                     │
│             │   Shared Lambda Layer   │                     │
│             │   (Common utilities)    │                     │
│             └─────────────────────────┘                     │
│                                                              │
└──────────────────────┬──────────────────┬───────────────────┘
                       │                  │
                       │                  │
           ┌───────────▼──────┐  ┌────────▼────────┐
           │   DynamoDB       │  │  CloudWatch     │
           │   Status         │  │  Logs           │
           │   Tracking       │  │                 │
           └──────────────────┘  └─────────────────┘
                       │
                       │ Updates
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  EXTERNAL SERVICES                           │
│                                                              │
│     ┌──────────┐              ┌──────────────┐             │
│     │  GitHub  │              │ HCP Terraform│             │
│     │   API    │              │     API      │             │
│     └──────────┘              └──────────────┘             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Slack Bot Layer

**Technology:** Python 3.12 + Slack Bolt SDK  
**File:** `src/main_with_api_gateway.py`

**Responsibilities:**
- Handle slash commands (`/aws-det-poc`, `/aws-det-onboard`)
- Display forms and modals
- Manage chat conversations (AI orchestration)
- Call API Gateway with validated data
- Display execution status to users

**Key Functions:**
- `aws_det_poc()` - Opens form modal
- `aws_det_chat()` - Starts chat session
- `handle_det_summary_submit()` - Submits to API Gateway

---

### 2. API Gateway

**Service:** AWS API Gateway (REST API)  
**Endpoint:** `POST /onboard`

**Configuration:**
```
Method: POST
Path: /onboard
Integration: AWS_PROXY → Step Functions
Authorization: None (add API key for production)
CORS: Enabled
```

**Request Format:**
```json
{
  "intake": {
    "project_name": "EMS",
    "environments": ["Dev", "Prod"],
    "regions": ["us-east-1"],
    "vpc_model": "Small",
    "terraform_repo": "myorg/ems-infra",
    "service_name": "EMS API",
    "business_justification": "...",
    "team_dl": "team@company.com",
    "team_channel": "C123456",
    "workspace_mode": "default",
    "workspace_names": {}
  },
  "slack_channel": "C123456",
  "slack_user": "U789012"
}
```

**Response Format:**
```json
{
  "executionArn": "arn:aws:states:...:execution:...:abc123",
  "startDate": "2026-06-07T10:00:00.000Z",
  "message": "Workflow started successfully"
}
```

---

### 3. Step Functions State Machine

**Service:** AWS Step Functions  
**Name:** `det-onboarding-prod-onboarding-v2`  
**Type:** Standard workflow

#### State Machine Flow

```
StartAt: ValidateIntake
     ↓
ValidateIntake (Lambda)
     ↓
CreateGitHubBranch (Lambda)
     ↓
CommitToGitHub (Lambda)
     ↓
CreateHCPProject (Lambda)
     ↓
CreateWorkspaces (Map - Parallel)
     ├─→ Dev Workspace (Lambda)
     ├─→ QA Workspace (Lambda)
     └─→ Prod Workspace (Lambda)
     ↓
ConfigureVariables (Map - Parallel)
     ├─→ Dev Variables (Lambda)
     ├─→ QA Variables (Lambda)
     └─→ Prod Variables (Lambda)
     ↓
End
```

#### Retry Configuration

Each step has automatic retry with exponential backoff:

```json
{
  "Retry": [
    {
      "ErrorEquals": ["States.ALL"],
      "IntervalSeconds": 2,
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    }
  ]
}
```

**Retry Pattern:**
- Attempt 1: Immediate
- Attempt 2: After 2 seconds
- Attempt 3: After 4 seconds
- Attempt 4: After 8 seconds

---

### 4. Lambda Functions

All functions use:
- **Runtime:** Python 3.12
- **Architecture:** x86_64
- **Memory:** 256-512 MB
- **Timeout:** 30-60 seconds
- **Logging:** CloudWatch Logs (JSON structured)

#### Function 1: validate_intake

**Purpose:** Validate and normalize intake data

**Location:** `terraform/modules/lambda/lambda_functions/validate_intake/handler.py`

**Process:**
1. Check required fields present
2. Validate email format (team_dl)
3. Validate region names
4. Normalize project name (slug, uppercase)
5. Create DynamoDB execution record
6. Return validated data

**Output:**
```json
{
  "intake": { /* validated data */ },
  "slack_channel": "C123456",
  "slack_user": "U789012",
  "execution_id": "abc123-def456"
}
```

---

#### Function 2: github_branch

**Purpose:** Create GitHub branch for intake document

**Location:** `terraform/modules/lambda/lambda_functions/github_branch/handler.py`

**Process:**
1. Get main branch SHA
2. Create branch: `{project-slug}-onboard`
3. Update DynamoDB status
4. Return branch name

**Uses Shared Layer:** `github_api.py`

**Output:**
```json
{
  "branch_name": "ems-onboard",
  "base_branch": "main",
  "created": true
}
```

---

#### Function 3: github_commit

**Purpose:** Commit intake document to GitHub

**Location:** `terraform/modules/lambda/lambda_functions/github_commit/handler.py`

**Process:**
1. Generate intake.yaml content
2. Commit to branch: `intake-files/{project}.yaml`
3. Update DynamoDB status
4. Return commit SHA and file URL

**Uses Shared Layer:** `github_api.py`, `det_intake.py`

**Output:**
```json
{
  "commit_sha": "abc123def456",
  "file_path": "intake-files/ems.yaml",
  "file_url": "https://github.com/..."
}
```

---

#### Function 4: hcp_project

**Purpose:** Create HCP Terraform project

**Location:** `terraform/modules/lambda/lambda_functions/hcp_project/handler.py`

**Process:**
1. Check if project exists
2. Create project if not exists
3. Update DynamoDB status
4. Return project ID

**Uses Shared Layer:** `hcp_terraform.py`

**Output:**
```json
{
  "project_id": "prj-abc123xyz",
  "project_name": "EMS",
  "created": true
}
```

---

#### Function 5: hcp_workspace

**Purpose:** Create HCP Terraform workspace

**Location:** `terraform/modules/lambda/lambda_functions/hcp_workspace/handler.py`

**Process:**
1. Generate workspace name: `{project-slug}-wspace-{env}`
2. Create workspace in HCP project
3. Link to GitHub VCS repository
4. Set working directory and branch
5. Update DynamoDB with workspace ID
6. Return workspace details

**Uses Shared Layer:** `hcp_terraform.py`

**Input (from Map state):**
```json
{
  "environment": "Dev",
  "project_id": "prj-abc123",
  "terraform_repo": "myorg/ems-infra",
  "branch_name": "ems-onboard"
}
```

**Output:**
```json
{
  "workspace_id": "ws-abc123",
  "workspace_name": "ems-wspace-dev",
  "environment": "Dev"
}
```

---

#### Function 6: hcp_vars

**Purpose:** Configure workspace variables

**Location:** `terraform/modules/lambda/lambda_functions/hcp_vars/handler.py`

**Process:**
1. Define variables for environment
2. Create/update each variable in workspace
3. Mark as Terraform or Environment variable
4. Update DynamoDB status
5. Return configuration status

**Uses Shared Layer:** `hcp_terraform.py`

**Variables Set:**
```hcl
# Terraform Variables
environment      = "dev"
region           = "us-east-1"
vpc_model        = "small"
project_name     = "ems"
service_name     = "EMS API"

# Environment Variables
TF_VAR_team_dl   = "team@company.com"
```

**Output:**
```json
{
  "workspace_id": "ws-abc123",
  "variables_configured": 6,
  "success": true
}
```

---

#### Function 7: status_tracker

**Purpose:** Update execution status in DynamoDB

**Location:** `terraform/modules/lambda/lambda_functions/status_tracker/handler.py`

**Process:**
1. Receive step update from Step Functions
2. Update DynamoDB execution record
3. Log to execution logs table
4. Return acknowledgment

**Tables Used:**
- `det-onboarding-prod-executions` (main status)
- `det-onboarding-prod-execution-logs` (detailed logs)

---

#### Function 8: completion_notifier

**Purpose:** Send completion notification to Slack

**Location:** `terraform/modules/lambda/lambda_functions/completion_notifier/handler.py`

**Process:**
1. Receive final workflow result
2. Format success/failure message
3. Include all resource links
4. Post to Slack channel
5. Update DynamoDB with final status

**Message Format:** (see USER_JOURNEY.md Step 7)

---

### 5. Shared Lambda Layer

**Purpose:** Common code used by multiple Lambda functions

**Location:** `terraform/modules/lambda/lambda_functions/shared_layer/python/`

**Contents:**

#### `github_api.py`
```python
def create_branch(owner, repo, branch_name, base_branch, token)
def create_or_update_file(owner, repo, branch, path, content, message, token)
def list_org_repositories(owner, token, query, limit)
```

#### `hcp_terraform.py`
```python
def create_project(org, project_name, token)
def create_workspace(org, workspace_name, project_id, token)
def link_vcs_repo(workspace_id, repo, branch, oauth_token_id, token)
def create_workspace_variable(workspace_id, key, value, category, token)
```

#### `det_intake.py`
```python
def validate_intake(intake_data)
def format_intake_yaml(intake_data)
def generate_workspace_names(project_slug, environments)
```

#### `dynamodb_helper.py`
```python
def create_execution_record(execution_id, intake, channel, user)
def update_step_status(execution_id, step_name, status, result)
def get_execution(execution_id)
```

#### `session_store.py`
```python
# Used only by Slack bot, not Lambda
```

**Dependencies in Layer:**
- `requests` - HTTP library
- `certifi` - SSL certificates
- `urllib3` - HTTP client
- `slack-sdk` - Slack API (for notifier)

---

### 6. DynamoDB Tables

#### Table 1: Executions

**Name:** `det-onboarding-prod-executions`  
**Primary Key:** `execution_id` (String)

**Schema:**
```python
{
  "execution_id": "abc123-def456-789012",      # Partition key
  "status": "RUNNING" | "SUCCEEDED" | "FAILED",
  "current_step": "CreateWorkspaces",
  "project_name": "EMS",
  "slack_channel": "C123456",
  "slack_user": "U789012",
  "created_at": "2026-06-07T10:00:00Z",
  "updated_at": "2026-06-07T10:00:15Z",
  "completed_at": "2026-06-07T10:00:42Z",      # When finished
  "ttl": 1720353600,                            # Auto-delete after 90 days
  "intake_data": { /* original intake */ },
  "steps": {
    "ValidateIntake": {
      "status": "SUCCEEDED",
      "started_at": "2026-06-07T10:00:00Z",
      "completed_at": "2026-06-07T10:00:03Z"
    },
    // ... other steps
  },
  "result": {
    "github_branch": "ems-onboard",
    "github_commit_sha": "abc123",
    "hcp_project_id": "prj-abc123",
    "workspaces": {
      "Dev": {"id": "ws-dev123", "name": "ems-wspace-dev"}
    }
  },
  "error_message": null
}
```

**Indexes:**
- GSI: `slack-channel-index` (slack_channel + created_at)
- GSI: `status-index` (status + created_at)

---

#### Table 2: Execution Logs

**Name:** `det-onboarding-prod-execution-logs`  
**Primary Key:** `execution_id` (String) + `timestamp` (Number)

**Schema:**
```python
{
  "execution_id": "abc123-def456",              # Partition key
  "timestamp": 1717752015000,                    # Sort key (milliseconds)
  "step_name": "CreateWorkspaces",
  "status": "RUNNING" | "SUCCEEDED" | "FAILED",
  "log_time": "2026-06-07T10:00:15Z",
  "result": { /* step result data */ },
  "error": null,
  "ttl": 1720353600                              # Auto-delete after 90 days
}
```

---

### 7. CloudWatch Logs

**Log Groups:**
```
/aws/lambda/det-onboarding-prod-validate-intake
/aws/lambda/det-onboarding-prod-github-branch
/aws/lambda/det-onboarding-prod-github-commit
/aws/lambda/det-onboarding-prod-hcp-project
/aws/lambda/det-onboarding-prod-hcp-workspace
/aws/lambda/det-onboarding-prod-hcp-vars
/aws/lambda/det-onboarding-prod-status-tracker
/aws/lambda/det-onboarding-prod-completion-notifier
/aws/states/det-onboarding-prod-onboarding
```

**Log Format (JSON):**
```json
{
  "timestamp": "2026-06-07T10:00:03.123Z",
  "level": "INFO",
  "message": "Workspace created successfully",
  "workspace_id": "ws-abc123",
  "environment": "Dev",
  "execution_id": "abc123-def456"
}
```

---

## Data Flow

### Complete Request Flow

```
1. User submits form in Slack
      ↓
2. Slack bot validates basic input
      ↓
3. Bot POST to API Gateway
      ↓
4. API Gateway triggers Step Functions
      ↓
5. Step Functions starts execution
      ↓
6. ValidateIntake Lambda
      ├─→ Validates data
      ├─→ Creates DynamoDB record
      └─→ Returns validated intake
      ↓
7. CreateGitHubBranch Lambda
      ├─→ Calls GitHub API
      ├─→ Creates branch
      └─→ Updates DynamoDB
      ↓
8. CommitToGitHub Lambda
      ├─→ Generates intake.yaml
      ├─→ Commits to branch
      └─→ Updates DynamoDB
      ↓
9. CreateHCPProject Lambda
      ├─→ Calls HCP Terraform API
      ├─→ Creates project
      └─→ Updates DynamoDB
      ↓
10. CreateWorkspaces (Map - Parallel)
      ├─→ Lambda for Dev
      │    ├─→ Creates workspace
      │    └─→ Links VCS repo
      ├─→ Lambda for QA
      │    ├─→ Creates workspace
      │    └─→ Links VCS repo
      └─→ Lambda for Prod
           ├─→ Creates workspace
           └─→ Links VCS repo
      ↓
11. ConfigureVariables (Map - Parallel)
      ├─→ Lambda for Dev workspace
      │    └─→ Sets variables
      ├─→ Lambda for QA workspace
      │    └─→ Sets variables
      └─→ Lambda for Prod workspace
           └─→ Sets variables
      ↓
12. CompletionNotifier Lambda
      ├─→ Formats message
      ├─→ Posts to Slack
      └─→ Updates DynamoDB (final)
      ↓
13. User receives notification
```

---

## Parallelization Strategy

### Sequential Steps (must run in order)
1. ValidateIntake
2. CreateGitHubBranch
3. CommitToGitHub
4. CreateHCPProject

**Reason:** Each depends on output of previous

### Parallel Steps (run simultaneously)

**Workspace Creation:**
```
CreateWorkspaces (Map state)
├─→ Dev (Lambda 5a)    │
├─→ QA (Lambda 5b)     │ Same time
└─→ Prod (Lambda 5c)   │
```

**Variable Configuration:**
```
ConfigureVariables (Map state)
├─→ Dev vars (Lambda 6a)    │
├─→ QA vars (Lambda 6b)     │ Same time
└─→ Prod vars (Lambda 6c)   │
```

**Time Savings:**
- Sequential: 3 envs × 10 sec = 30 sec
- Parallel: max(10, 10, 10) = 10 sec
- **Savings: 20 seconds (67% faster)**

---

## Error Handling

### Retry Logic

**Per-step automatic retry:**
```
Attempt 1 → Fail
    ↓ (wait 2 sec)
Attempt 2 → Fail
    ↓ (wait 4 sec)
Attempt 3 → Fail
    ↓ (wait 8 sec)
Attempt 4 → Fail
    ↓
Workflow fails
```

### Error Types

#### Transient Errors (retryable)
- Network timeouts
- API rate limits
- Temporary service unavailability

#### Permanent Errors (not retryable)
- Invalid credentials
- Resource already exists (handled gracefully)
- Permission denied

### Partial Success Handling

**Scenario:** Dev and QA workspaces succeed, Prod fails

**Behavior:**
```
Map state completes with partial results
    ↓
ConfigureVariables runs only for Dev and QA
    ↓
Notification shows:
  ✓ Dev workspace created
  ✓ QA workspace created
  ✗ Prod workspace failed (see error)
```

**User action:** Can manually create Prod or resubmit

---

## Security

### Secrets Management

**Tokens stored in:**
- Lambda environment variables (encrypted at rest)
- Passed via Terraform variables
- Never logged or exposed

**Environment Variables:**
```bash
GITHUB_TOKEN="ghp_***"                      # GitHub API
HCP_TERRAFORM_TOKEN="***"                   # HCP Terraform
HCP_TERRAFORM_VCS_OAUTH_TOKEN_ID="ot-***"  # VCS OAuth
SLACK_BOT_TOKEN="xoxb-***"                  # Slack notifications
```

### IAM Roles

#### API Gateway Role
```json
{
  "Action": "states:StartExecution",
  "Resource": "arn:aws:states:*:*:stateMachine:det-onboarding-*"
}
```

#### Lambda Execution Role
```json
{
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "dynamodb:PutItem",
    "dynamodb:GetItem",
    "dynamodb:UpdateItem",
    "dynamodb:Query"
  ],
  "Resource": "*"
}
```

#### Step Functions Role
```json
{
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:*:*:function:det-onboarding-*"
}
```

---

## Scalability

### Concurrent Executions

**Step Functions:** No limit (standard workflow)  
**Lambda:** Account-level concurrent execution limit (1000 default, increasable)  
**API Gateway:** 10,000 requests/sec (soft limit, increasable)

### Workload Patterns

**Low Volume (< 100/day):**
- Cost: ~$2-3/month
- No throttling
- Default limits sufficient

**Medium Volume (< 1000/day):**
- Cost: ~$20-30/month
- May need Lambda concurrency increase
- DynamoDB on-demand handles load

**High Volume (> 1000/day):**
- Cost: ~$200-300/month
- Request Lambda concurrency increase
- Consider DynamoDB provisioned capacity
- Add API Gateway caching

---

## Monitoring

### CloudWatch Metrics

**Step Functions:**
- ExecutionsStarted
- ExecutionsSucceeded
- ExecutionsFailed
- ExecutionTime (avg, max, p99)

**Lambda:**
- Invocations
- Errors
- Duration
- Throttles
- ConcurrentExecutions

**API Gateway:**
- Count (requests)
- 4XXError
- 5XXError
- Latency

### Alarms

**Critical:**
- Step Functions execution failure rate > 10%
- Lambda error rate > 5%
- API Gateway 5XX errors > 1%

**Warning:**
- Lambda duration > 20 seconds
- DynamoDB throttles > 0
- Lambda concurrent executions > 80% of limit

---

## Cost Breakdown

### Per Execution (~1000/month)

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| API Gateway | 1,000 requests | $3.50/million | $0.004 |
| Step Functions | 1,000 executions × 6 transitions | $0.025/1000 transitions | $0.15 |
| Lambda invocations | 8,000 invocations | $0.20/million | $0.002 |
| Lambda compute | 8,000 × 1 sec × 512 MB | $0.0000166667/GB-sec | $1.07 |
| DynamoDB | 10,000 writes, 5,000 reads | On-demand pricing | $1.50 |
| CloudWatch Logs | 1 GB ingested, 1 GB stored | $0.50/GB ingested + storage | $0.60 |
| **Total** | | | **~$3.38/month** |

### Additional Costs

- Data transfer: Minimal (< $0.01)
- VPC: Not used (Lambda runs without VPC)
- NAT Gateway: Not used
- Secrets Manager: Not used (env vars sufficient)

---

## Deployment

### Terraform Modules

```
terraform/
├── main.tf                  # Root module
├── variables.tf             # Input variables
├── outputs.tf              # Output values
├── modules/
│   ├── api_gateway/        # API Gateway REST API
│   ├── step_functions/     # State machine definition
│   ├── lambda/             # All Lambda functions + layer
│   ├── dynamodb/           # Execution tables
│   └── iam/                # Roles and policies
```

### Deployment Steps

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

**Resources Created:** ~30 AWS resources

**Deployment Time:** ~3-5 minutes

---

## Maintenance

### Regular Tasks

**Weekly:**
- Review failed executions in DynamoDB
- Check CloudWatch alarms
- Review Lambda error logs

**Monthly:**
- Analyze execution patterns
- Optimize Lambda memory allocation
- Review and adjust timeouts
- Check for API rate limit issues

**Quarterly:**
- Update Lambda runtimes
- Review and rotate tokens
- Update Terraform modules
- Performance optimization

---

## Summary

The architecture provides:

✅ **Serverless** - No servers to manage  
✅ **Scalable** - Handles 1-10,000+ requests/day  
✅ **Reliable** - Automatic retries, error handling  
✅ **Observable** - Full logging and monitoring  
✅ **Cost-Effective** - Pay only for use (~$3/month for 1000 requests)  
✅ **Maintainable** - Modular, well-documented  
✅ **Secure** - IAM roles, encrypted secrets  
✅ **Fast** - 30-45 second execution, parallel workspaces

---

**Architecture designed for production reliability and scale. 🏗️**
