# User Journey - Complete Step-by-Step Flow

## Overview

This document walks through the complete onboarding journey from the moment a user opens Slack to the final notification.

---

## 🎯 Complete Journey Map

```
┌─────────────────────────────────────────────────────────────────┐
│ USER IN SLACK                                                   │
│ Types: /aws-det-poc                                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SLACK MODAL OPENS                                               │
│ User fills form: Project, Environments, VPC size, etc.         │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ USER CLICKS SUBMIT                                              │
│ Slack app receives form data                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ API GATEWAY                                                     │
│ POST /onboard                                                   │
│ Receives: intake data, slack_channel, slack_user               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP FUNCTIONS STARTS                                           │
│ Execution ID: abc123-def456                                     │
│ State Machine: det-onboarding-prod-onboarding-v2               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ Lambda Execution Flow  │
        └────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌──────┐      ┌──────────┐      ┌─────────┐
│Step 1│      │Step 2-6  │      │Step 7-8 │
│Track │ ───▶ │Workflow  │ ───▶ │Notify   │
└──────┘      └──────────┘      └─────────┘
```

---

## 📱 Step-by-Step User Journey

### **Step 0: User Initiates Request**

**Time: T+0 seconds**

**User Action:**
```
User opens Slack → Types: /aws-det-poc → Presses Enter
```

**What Happens:**
1. Slack sends command to your bot server (`main_with_api_gateway.py`)
2. Bot calls `welcome_page()` function
3. Slack modal opens with form

**User Sees:**
```
┌─────────────────────────────────────┐
│  AWS DET Onboarding Request         │
├─────────────────────────────────────┤
│                                     │
│  Project Name: [____________]       │
│                                     │
│  Terraform Repo: [▼ Select repo]   │
│                                     │
│  Team Channel: [▼ Select channel]  │
│                                     │
│  Environments: ☐ Dev ☐ QA ☐ Prod   │
│                                     │
│  Regions: ☐ us-east-1 ☐ us-west-2  │
│                                     │
│  VPC Model: ○ Small ○ Medium ○ Big │
│                                     │
│  Service Name: [____________]       │
│                                     │
│  Business Justification:            │
│  [_____________________________]    │
│                                     │
│  Team DL: [____________@company.com]│
│                                     │
│           [Cancel]  [Submit]        │
└─────────────────────────────────────┘
```

---

### **Step 1: User Fills & Submits Form**

**Time: T+30 seconds** (user filling form)

**User Action:**
```
Fills form with:
- Project Name: "EMS Platform"
- Terraform Repo: "adityajhacse/test"
- Team Channel: "#ems-team"
- Environments: [✓] Dev [✓] QA [✓] Prod
- Regions: [✓] us-east-1
- VPC Model: ● Small
- Service Name: "EMS API Service"
- Business Justification: "New microservice for EMS platform"
- Team DL: "ems-team@company.com"

Clicks: [Submit]
```

**What Happens:**
1. Slack sends form data to bot
2. Bot extracts intake data
3. Bot calls API Gateway

**Code Execution:**
```python
# File: src/main_with_api_gateway.py
# Function: handle_det_summary_submit()

@app.view("det_summary_modal")
def handle_det_summary_submit(ack, body, view, client):
    # Extract form data
    full_intake = {
        "project_name": "EMS Platform",
        "terraform_repo": "adityajhacse/test",
        "environments": ["Dev", "QA", "Prod"],
        "regions": ["us-east-1"],
        "vpc_model": "Small",
        "service_name": "EMS API Service",
        "business_justification": "New microservice for EMS platform",
        "team_dl": "ems-team@company.com"
    }
    
    # Call API Gateway
    result = api_client.trigger_onboarding(
        intake=full_intake,
        slack_channel="C0123456789",
        slack_user="U0987654321"
    )
```

**User Sees:**
```
Processing your request...
⏳ Starting onboarding workflow
```

---

### **Step 2: API Gateway Receives Request**

**Time: T+31 seconds**

**HTTP Request:**
```http
POST https://abc123.execute-api.us-east-1.amazonaws.com/prod/onboard
Content-Type: application/json

{
  "intake": {
    "project_name": "EMS Platform",
    "project_slug": "ems-platform",
    "project_upper": "EMS-PLATFORM",
    "terraform_repo": "adityajhacse/test",
    "team_channel": "ems-team",
    "environments": ["Dev", "QA", "Prod"],
    "regions": ["us-east-1"],
    "vpc_model": "Small",
    "service_name": "EMS API Service",
    "business_justification": "New microservice for EMS platform",
    "team_dl": "ems-team@company.com",
    "workspace_mode": "default",
    "workspace_names": {}
  },
  "slack_channel": "C0123456789",
  "slack_user": "U0987654321"
}
```

**What Happens:**
1. API Gateway validates request
2. API Gateway invokes Step Functions
3. Returns execution ARN

**API Response:**
```json
{
  "executionArn": "arn:aws:states:us-east-1:123456789012:execution:det-onboarding-prod-onboarding-v2:abc123-def456",
  "startDate": "2024-06-05T10:00:00.123Z",
  "message": "Onboarding workflow started successfully"
}
```

**User Sees in Slack:**
```
🎉 Onboarding workflow started for EMS Platform

Execution ID: abc123-def456
Started by: @john.doe

The workflow is processing in the background.
You'll be notified when it completes.
```

---

### **Step 3: Step Functions Execution Begins**

**Time: T+31.2 seconds**

**Step Functions State Machine Starts:**
```
State Machine: det-onboarding-prod-onboarding-v2
Execution ID: abc123-def456
Execution ARN: arn:aws:states:us-east-1:123456789012:execution:det-onboarding-prod-onboarding-v2:abc123-def456
Status: RUNNING
```

**Initial State:**
```json
{
  "intake": { /* all form data */ },
  "slack_channel": "C0123456789",
  "slack_user": "U0987654321"
}
```

---

## 🔄 Lambda Execution Flow

### **Lambda 1: InitializeTracking (status_tracker)**

**Time: T+31.3 seconds**

**Purpose:** Create initial DynamoDB record

**Input to Lambda:**
```json
{
  "action": "start",
  "execution_id": "abc123-def456",
  "intake": { /* all form data */ },
  "slack_channel": "C0123456789",
  "slack_user": "U0987654321"
}
```

**Lambda Execution:**
```python
# File: lambda_functions/status_tracker/handler.py

def lambda_handler(event, context):
    from dynamodb_helper import get_helper
    
    db = get_helper()
    
    # Create initial record
    record = db.create_execution_record(
        execution_id="abc123-def456",
        intake=intake_data,
        slack_channel="C0123456789",
        slack_user="U0987654321"
    )
    
    return {"statusCode": 200, "tracked": True}
```

**DynamoDB Record Created:**
```json
{
  "execution_id": "abc123-def456",
  "status": "RUNNING",
  "current_step": "ValidateIntake",
  "project_name": "EMS Platform",
  "project_slug": "ems-platform",
  "slack_channel": "C0123456789",
  "slack_user": "U0987654321",
  "created_at": "2024-06-05T10:00:00.123Z",
  "updated_at": "2024-06-05T10:00:00.123Z",
  "ttl": 1712847600,
  "intake_data": { /* complete form data */ },
  "steps": {
    "ValidateIntake": {"status": "PENDING"},
    "CreateGitHubBranch": {"status": "PENDING"},
    "CommitToGitHub": {"status": "PENDING"},
    "CreateHCPProject": {"status": "PENDING"},
    "CreateWorkspaces": {"status": "PENDING"},
    "ConfigureVariables": {"status": "PENDING"}
  },
  "results": {},
  "errors": []
}
```

**CloudWatch Log:**
```
[INFO] 2024-06-05T10:00:00.123Z Creating execution record
[INFO] 2024-06-05T10:00:00.456Z Created execution record: abc123-def456
```

---

### **Lambda 2: ValidateIntake (validate_intake)**

**Time: T+32 seconds**

**Purpose:** Validate form data and normalize values

**Input to Lambda:**
```json
{
  "intake": { /* form data */ },
  "slack_channel": "C0123456789",
  "slack_user": "U0987654321",
  "execution_id": "abc123-def456"
}
```

**Lambda Execution:**
```python
# File: lambda_functions/validate_intake/handler.py

def lambda_handler(event, context):
    from det_intake import validate_intake
    
    intake_data = event.get("intake", {})
    
    # Validate intake
    validation_result = validate_intake(intake_data)
    
    # Result:
    # {
    #   "valid": True,
    #   "intake": { normalized data },
    #   "missing_fields": [],
    #   "errors": []
    # }
    
    if not validation_result["valid"]:
        return {
            "statusCode": 400,
            "valid": False,
            "missing_fields": validation_result["missing_fields"],
            "errors": validation_result["errors"]
        }
    
    return {
        "statusCode": 200,
        "valid": True,
        "intake": validation_result["intake"]
    }
```

**Validation Checks:**
1. ✅ Project name present: "EMS Platform"
2. ✅ Terraform repo valid: "adityajhacse/test"
3. ✅ Environments valid: ["Dev", "QA", "Prod"]
4. ✅ Regions valid: ["us-east-1"]
5. ✅ VPC model valid: "Small"
6. ✅ Team DL is email: "ems-team@company.com"

**Output:**
```json
{
  "statusCode": 200,
  "valid": true,
  "intake": {
    "project_name": "EMS Platform",
    "project_slug": "ems-platform",
    "project_upper": "EMS-PLATFORM",
    /* ... normalized data ... */
  }
}
```

**CloudWatch Log:**
```
[INFO] 2024-06-05T10:00:01.000Z Validating intake data
[INFO] 2024-06-05T10:00:01.123Z Validation successful for project: EMS Platform
```

---

### **Lambda 3: TrackValidationSuccess (status_tracker)**

**Time: T+32.5 seconds**

**Purpose:** Update DynamoDB with validation success

**Input:**
```json
{
  "action": "step_update",
  "execution_id": "abc123-def456",
  "step_name": "ValidateIntake",
  "step_status": "SUCCEEDED",
  "result": { /* validated intake */ }
}
```

**DynamoDB Update:**
```json
{
  "execution_id": "abc123-def456",
  "current_step": "CreateGitHubBranch",  // ← Updated
  "steps": {
    "ValidateIntake": {
      "status": "SUCCEEDED",  // ← Updated
      "started_at": "2024-06-05T10:00:01.000Z",
      "completed_at": "2024-06-05T10:00:01.500Z"
    }
  }
}
```

---

### **Lambda 4: CreateGitHubBranch (github_branch)**

**Time: T+33 seconds**

**Purpose:** Create feature branch in GitHub repository

**Input:**
```json
{
  "intake": { /* validated data */ },
  "slack_channel": "C0123456789",
  "slack_user": "U0987654321",
  "execution_id": "abc123-def456"
}
```

**Lambda Execution:**
```python
# File: lambda_functions/github_branch/handler.py

def lambda_handler(event, context):
    from github_api import ensure_git_branch, sanitize_git_branch_from_project_name
    
    intake = event.get("intake", {})
    project_name = intake.get("project_name", "")  # "EMS Platform"
    
    # Get GitHub config from environment variables
    owner = os.environ.get("GITHUB_OWNER")  # "adityajhacse"
    repo = os.environ.get("GITHUB_REPO")     # "test"
    token = os.environ.get("GITHUB_TOKEN")   # "ghp_b4cX..."
    base_branch = "main"
    
    # Create safe branch name
    branch_name = sanitize_git_branch_from_project_name(project_name)
    # Result: "ems-platform"
    
    # Create branch via GitHub API
    ensure_git_branch(owner, repo, branch_name, base_branch, token)
    
    return {
        "statusCode": 200,
        "branch_name": "ems-platform",
        "branch_created": True,
        "repository": "adityajhacse/test"
    }
```

**GitHub API Call:**
```http
GET https://api.github.com/repos/adityajhacse/test/git/ref/heads/ems-platform
Response: 404 (branch doesn't exist)

GET https://api.github.com/repos/adityajhacse/test/git/ref/heads/main
Response: 200 {"object": {"sha": "abc123..."}}

POST https://api.github.com/repos/adityajhacse/test/git/refs
Body: {
  "ref": "refs/heads/ems-platform",
  "sha": "abc123..."
}
Response: 201 Created
```

**Result:**
- ✅ Branch created: `ems-platform`
- ✅ Based on: `main`
- ✅ Repository: `adityajhacse/test`

**CloudWatch Log:**
```
[INFO] 2024-06-05T10:00:02.000Z Creating branch 'ems-platform' in adityajhacse/test from main
[INFO] 2024-06-05T10:00:02.789Z Branch 'ems-platform' ready
```

---

### **Lambda 5: TrackGitHubBranchSuccess (status_tracker)**

**Time: T+33.5 seconds**

**DynamoDB Update:**
```json
{
  "current_step": "CommitToGitHub",
  "steps": {
    "CreateGitHubBranch": {
      "status": "SUCCEEDED",
      "result": "ems-platform",
      "started_at": "2024-06-05T10:00:02.000Z",
      "completed_at": "2024-06-05T10:00:02.800Z"
    }
  }
}
```

---

### **Lambda 6: CommitToGitHub (github_commit)**

**Time: T+34 seconds**

**Purpose:** Create AFT JSON file and commit to GitHub

**Input:**
```json
{
  "intake": { /* validated data */ },
  "branch_name": "ems-platform",
  "slack_channel": "C0123456789",
  "slack_user": "U0987654321"
}
```

**Lambda Execution:**
```python
# File: lambda_functions/github_commit/handler.py

def lambda_handler(event, context):
    from github_api import build_github_intake_document, put_repository_json_file
    
    intake = event.get("intake", {})
    branch_name = event.get("branch_name")  # "ems-platform"
    slack_user_data = {"id": event.get("slack_user")}
    
    # BUILD AFT JSON PAYLOAD
    file_path, aft_json = build_github_intake_document(intake, slack_user_data)
    # file_path: "requests/ems-platform-dev.json"
    # aft_json: { "request_id": "ems-platform-dev", "aft": {...} }
    
    # COMMIT TO GITHUB
    result = put_repository_json_file(
        owner="adityajhacse",
        repo="test",
        path=file_path,
        data=aft_json,
        commit_message="DET intake ems-platform-dev",
        token=os.environ.get("GITHUB_TOKEN"),
        branch=branch_name
    )
    
    return {
        "statusCode": 200,
        "commit_sha": result["commit"]["sha"],
        "file_url": result["content"]["html_url"],
        "file_path": file_path,
        "request_id": "ems-platform-dev"
    }
```

**AFT JSON Created:**
```json
{
  "request_id": "ems-platform-dev",
  "aft": {
    "control_tower_parameters": {
      "AccountEmail": "abc@example.com",
      "AccountName": "EMS Platform Dev",
      "ManagedOrganizationalUnit": "Dev (ou-1234567890)",
      "SSOUserEmail": "ems-team@company.com",
      "SSOUserFirstName": "Aditya",
      "SSOUserLastName": "jha"
    },
    "custom_fields": {
      "github_actions_subject_patterns": [
        "repo:SF-BT-NonProd/edd-platform-aws-sample-lambda:ref:refs/heads/main"
      ],
      "enable_private_dns_rfc": true,
      "project_name": "ems-platform",
      "terraform_cloud_project": "EMS Platform",
      "region": "us-east-1",
      "vpc_size": "small"
    },
    "change_management_parameters": {
      "change_requested_by": "U0987654321",
      "change_reason": "New microservice for EMS platform"
    }
  }
}
```

**GitHub API Calls:**
```http
1. GET file to check if exists
   GET https://api.github.com/repos/adityajhacse/test/contents/requests/ems-platform-dev.json?ref=ems-platform
   Response: 404 (new file)

2. Commit file
   PUT https://api.github.com/repos/adityajhacse/test/contents/requests/ems-platform-dev.json
   Body: {
     "message": "DET intake ems-platform-dev",
     "content": "<base64 encoded JSON>",
     "branch": "ems-platform"
   }
   Response: 201 Created
```

**Result:**
- ✅ File created: `requests/ems-platform-dev.json`
- ✅ Branch: `ems-platform`
- ✅ Commit SHA: `def456789...`
- ✅ File URL: `https://github.com/adityajhacse/test/blob/ems-platform/requests/ems-platform-dev.json`

**CloudWatch Log:**
```
[INFO] 2024-06-05T10:00:03.000Z Committing requests/ems-platform-dev.json to adityajhacse/test:ems-platform
[INFO] 2024-06-05T10:00:03.890Z Committed successfully: https://github.com/...
```

---

### **Lambda 7: TrackGitHubCommitSuccess (status_tracker)**

**Time: T+35 seconds**

**DynamoDB Update:**
```json
{
  "current_step": "CreateHCPProject",
  "steps": {
    "CommitToGitHub": {
      "status": "SUCCEEDED",
      "result": {
        "file_url": "https://github.com/adityajhacse/test/blob/ems-platform/requests/ems-platform-dev.json",
        "commit_sha": "def456789..."
      },
      "completed_at": "2024-06-05T10:00:03.900Z"
    }
  },
  "results": {
    "github_file_url": "https://github.com/adityajhacse/test/blob/ems-platform/requests/ems-platform-dev.json"
  }
}
```

---

### **Lambda 8: CreateHCPProject (hcp_project)**

**Time: T+36 seconds**

**Purpose:** Create HCP Terraform project

**Input:**
```json
{
  "intake": {
    "project_upper": "EMS-PLATFORM",
    "project_name": "EMS Platform"
  }
}
```

**Lambda Execution:**
```python
# File: lambda_functions/hcp_project/handler.py

def lambda_handler(event, context):
    from hcp_terraform import _create_project, _hcp_config
    
    intake = event.get("intake", {})
    project_name = intake.get("project_upper")  # "EMS-PLATFORM"
    
    # Get HCP config from environment variables
    token = os.environ.get("HCP_TERRAFORM_TOKEN")  # "xZ4z56mY..."
    organization = os.environ.get("HCP_TERRAFORM_ORG")  # "adityajhacse"
    base_url = "https://app.terraform.io"
    
    # CREATE HCP PROJECT
    project = _create_project(
        project_name=project_name,
        token=token,
        organization=organization,
        base_url=base_url
    )
    
    return {
        "statusCode": 200,
        "project_id": project["id"],      # "prj-abc123xyz789"
        "project_name": project["name"]   # "EMS-PLATFORM"
    }
```

**HCP Terraform API Call:**
```http
POST https://app.terraform.io/api/v2/organizations/adityajhacse/projects
Authorization: Bearer xZ4z56mY...
Content-Type: application/vnd.api+json

Body:
{
  "data": {
    "type": "projects",
    "attributes": {
      "name": "EMS-PLATFORM"
    }
  }
}

Response: 201 Created
{
  "data": {
    "id": "prj-abc123xyz789",
    "type": "projects",
    "attributes": {
      "name": "EMS-PLATFORM",
      "created-at": "2024-06-05T10:00:04.567Z"
    }
  }
}
```

**Result:**
- ✅ HCP Project Created: "EMS-PLATFORM"
- ✅ Project ID: `prj-abc123xyz789`
- ✅ Organization: `adityajhacse`

**CloudWatch Log:**
```
[INFO] 2024-06-05T10:00:04.000Z Creating project 'EMS-PLATFORM' in HCP org 'adityajhacse'
[INFO] 2024-06-05T10:00:04.890Z Project created: EMS-PLATFORM (ID: prj-abc123xyz789)
```

---

### **Lambda 9: TrackHCPProjectSuccess (status_tracker)**

**Time: T+37 seconds**

**DynamoDB Update:**
```json
{
  "current_step": "CreateWorkspaces",
  "steps": {
    "CreateHCPProject": {
      "status": "SUCCEEDED",
      "result": {
        "project_id": "prj-abc123xyz789",
        "project_name": "EMS-PLATFORM"
      }
    }
  },
  "results": {
    "hcp_project_id": "prj-abc123xyz789"
  }
}
```

---

### **Lambdas 10-12: CreateWorkspaces (hcp_workspace) - PARALLEL EXECUTION**

**Time: T+38 seconds** (all 3 run simultaneously)

**Purpose:** Create HCP Terraform workspaces for each environment

#### **Lambda 10a: Dev Workspace**

**Input:**
```json
{
  "environment": "Dev",
  "project_id": "prj-abc123xyz789",
  "project_slug": "ems-platform",
  "terraform_repo": "adityajhacse/test",
  "workspace_names": {}
}
```

**Lambda Execution:**
```python
# File: lambda_functions/hcp_workspace/handler.py

def lambda_handler(event, context):
    from hcp_terraform import _create_workspace, _resolve_workspace_name
    
    environment = "Dev"
    project_id = "prj-abc123xyz789"
    project_slug = "ems-platform"
    terraform_repo = "adityajhacse/test"
    
    # Determine workspace name
    workspace_name = _resolve_workspace_name(
        project_slug=project_slug,
        environment=environment,
        workspace_names={}
    )
    # Result: "ems-platform-dev"
    
    environment_slug = "dev"
    
    # CREATE WORKSPACE
    workspace = _create_workspace(
        workspace_name=workspace_name,
        environment_slug=environment_slug,
        project_id=project_id,
        terraform_repo=terraform_repo,
        token=os.environ.get("HCP_TERRAFORM_TOKEN"),
        organization=os.environ.get("HCP_TERRAFORM_ORG"),
        base_url="https://app.terraform.io"
    )
    
    return {
        "statusCode": 200,
        "workspace_id": workspace["id"],        # "ws-dev123abc"
        "workspace_name": workspace["name"],    # "ems-platform-dev"
        "environment": "Dev"
    }
```

**HCP API Calls:**
```http
1. Ensure branch exists
   GET https://api.github.com/repos/adityajhacse/test/git/ref/heads/dev
   Response: 404
   
   POST https://api.github.com/repos/adityajhacse/test/git/refs
   Body: {"ref": "refs/heads/dev", "sha": "abc123..."}
   Response: 201 Created

2. Create workspace
   POST https://app.terraform.io/api/v2/organizations/adityajhacse/workspaces
   Body:
   {
     "data": {
       "type": "workspaces",
       "attributes": {
         "name": "ems-platform-dev",
         "vcs-repo": {
           "identifier": "adityajhacse/test",
           "branch": "dev",
           "oauth-token-id": "ghp_b4cX..."
         }
       },
       "relationships": {
         "project": {
           "data": {"id": "prj-abc123xyz789", "type": "projects"}
         }
       }
     }
   }
   Response: 201 Created
```

**Result:**
- ✅ Workspace: `ems-platform-dev`
- ✅ Workspace ID: `ws-dev123abc`
- ✅ VCS Branch: `dev`

#### **Lambda 10b: QA Workspace** (runs in parallel)

**Same process as Dev, creates:**
- ✅ Workspace: `ems-platform-qa`
- ✅ Workspace ID: `ws-qa456def`
- ✅ VCS Branch: `qa`

#### **Lambda 10c: Prod Workspace** (runs in parallel)

**Same process, creates:**
- ✅ Workspace: `ems-platform-prod`
- ✅ Workspace ID: `ws-prod789ghi`
- ✅ VCS Branch: `prod`

**Time taken:** ~5 seconds (all 3 in parallel)

**CloudWatch Logs (3 separate streams):**
```
[ws-dev] [INFO] Creating workspace 'ems-platform-dev' for Dev
[ws-qa]  [INFO] Creating workspace 'ems-platform-qa' for QA
[ws-prod][INFO] Creating workspace 'ems-platform-prod' for Prod
[ws-dev] [INFO] Workspace created: ems-platform-dev (ID: ws-dev123abc)
[ws-qa]  [INFO] Workspace created: ems-platform-qa (ID: ws-qa456def)
[ws-prod][INFO] Workspace created: ems-platform-prod (ID: ws-prod789ghi)
```

---

### **Lambda 13: TrackWorkspaceComplete (status_tracker)**

**Time: T+43 seconds**

**DynamoDB Update:**
```json
{
  "current_step": "ConfigureVariables",
  "steps": {
    "CreateWorkspaces": {
      "status": "SUCCEEDED",
      "result": [
        {"workspace_id": "ws-dev123abc", "workspace_name": "ems-platform-dev", "environment": "Dev"},
        {"workspace_id": "ws-qa456def", "workspace_name": "ems-platform-qa", "environment": "QA"},
        {"workspace_id": "ws-prod789ghi", "workspace_name": "ems-platform-prod", "environment": "Prod"}
      ]
    }
  },
  "results": {
    "workspaces": {
      "Dev": {"workspace_id": "ws-dev123abc", "workspace_name": "ems-platform-dev"},
      "QA": {"workspace_id": "ws-qa456def", "workspace_name": "ems-platform-qa"},
      "Prod": {"workspace_id": "ws-prod789ghi", "workspace_name": "ems-platform-prod"}
    }
  }
}
```

---

### **Lambdas 14-16: ConfigureVariables (hcp_vars) - PARALLEL EXECUTION**

**Time: T+44 seconds**

**Purpose:** Configure environment variables for each workspace

#### **Lambda 14a: Dev Workspace Variables**

**Input:**
```json
{
  "workspace_id": "ws-dev123abc",
  "workspace_name": "ems-platform-dev",
  "environment": "Dev"
}
```

**Lambda Execution:**
```python
# File: lambda_functions/hcp_vars/handler.py

def lambda_handler(event, context):
    from hcp_terraform import _set_workspace_env_vars
    
    workspace_id = "ws-dev123abc"
    
    # SET ENVIRONMENT VARIABLES
    _set_workspace_env_vars(
        workspace_id=workspace_id,
        token=os.environ.get("HCP_TERRAFORM_TOKEN"),
        base_url="https://app.terraform.io"
    )
    
    return {
        "statusCode": 200,
        "workspace_id": workspace_id,
        "configured": True,
        "variables_set": ["TFC_AWS_PROVIDER_AUTH", "TFC_AWS_RUN_ROLE_ARN"]
    }
```

**HCP API Calls:**
```http
1. Set TFC_AWS_PROVIDER_AUTH
   POST https://app.terraform.io/api/v2/workspaces/ws-dev123abc/vars
   Body:
   {
     "data": {
       "type": "vars",
       "attributes": {
         "key": "TFC_AWS_PROVIDER_AUTH",
         "value": "true",
         "category": "env",
         "hcl": false,
         "sensitive": false
       }
     }
   }
   Response: 201 Created

2. Set TFC_AWS_RUN_ROLE_ARN
   POST https://app.terraform.io/api/v2/workspaces/ws-dev123abc/vars
   Body:
   {
     "data": {
       "type": "vars",
       "attributes": {
         "key": "TFC_AWS_RUN_ROLE_ARN",
         "value": "arn:aws:iam::916657620953:role/HCP-terraform-role",
         "category": "env",
         "hcl": false,
         "sensitive": false
       }
     }
   }
   Response: 201 Created
```

**Result:**
- ✅ Variable 1: `TFC_AWS_PROVIDER_AUTH = true`
- ✅ Variable 2: `TFC_AWS_RUN_ROLE_ARN = arn:aws:iam::916657620953:role/HCP-terraform-role`

#### **Lambda 14b: QA Workspace Variables** (parallel)
Same process for `ws-qa456def`

#### **Lambda 14c: Prod Workspace Variables** (parallel)
Same process for `ws-prod789ghi`

**Time taken:** ~3 seconds (all 3 in parallel)

**CloudWatch Logs:**
```
[ws-dev-vars] [INFO] Setting environment variables for workspace ws-dev123abc
[ws-qa-vars]  [INFO] Setting environment variables for workspace ws-qa456def
[ws-prod-vars][INFO] Setting environment variables for workspace ws-prod789ghi
[ws-dev-vars] [INFO] Variables configured for workspace ems-platform-dev
[ws-qa-vars]  [INFO] Variables configured for workspace ems-platform-qa
[ws-prod-vars][INFO] Variables configured for workspace ems-platform-prod
```

---

### **Lambda 17: TrackVariablesComplete (status_tracker)**

**Time: T+47 seconds**

**DynamoDB Update:**
```json
{
  "current_step": "ConfigureVariables",
  "steps": {
    "ConfigureVariables": {
      "status": "SUCCEEDED",
      "result": [
        {"workspace_id": "ws-dev123abc", "configured": true},
        {"workspace_id": "ws-qa456def", "configured": true},
        {"workspace_id": "ws-prod789ghi", "configured": true}
      ]
    }
  }
}
```

---

### **Lambda 18: TrackCompletion (status_tracker)**

**Time: T+48 seconds**

**Purpose:** Mark execution as completed

**Input:**
```json
{
  "action": "complete",
  "execution_id": "abc123-def456",
  "result": { /* all results from previous steps */ }
}
```

**DynamoDB Final Update:**
```json
{
  "execution_id": "abc123-def456",
  "status": "SUCCEEDED",  // ← Final status
  "current_step": "ConfigureVariables",
  "completed_at": "2024-06-05T10:00:18.000Z",  // ← Completion time
  "steps": {
    "ValidateIntake": {"status": "SUCCEEDED", "completed_at": "..."},
    "CreateGitHubBranch": {"status": "SUCCEEDED", "completed_at": "..."},
    "CommitToGitHub": {"status": "SUCCEEDED", "completed_at": "..."},
    "CreateHCPProject": {"status": "SUCCEEDED", "completed_at": "..."},
    "CreateWorkspaces": {"status": "SUCCEEDED", "completed_at": "..."},
    "ConfigureVariables": {"status": "SUCCEEDED", "completed_at": "..."}
  },
  "results": {
    "project_id": "prj-abc123xyz789",
    "project_name": "EMS-PLATFORM",
    "file_url": "https://github.com/adityajhacse/test/blob/ems-platform/requests/ems-platform-dev.json",
    "branch_name": "ems-platform",
    "workspaces": {
      "Dev": {"workspace_id": "ws-dev123abc", "workspace_name": "ems-platform-dev"},
      "QA": {"workspace_id": "ws-qa456def", "workspace_name": "ems-platform-qa"},
      "Prod": {"workspace_id": "ws-prod789ghi", "workspace_name": "ems-platform-prod"}
    },
    "configured_workspaces": [
      {"workspace_id": "ws-dev123abc", "configured": true},
      {"workspace_id": "ws-qa456def", "configured": true},
      {"workspace_id": "ws-prod789ghi", "configured": true}
    ]
  }
}
```

---

### **Lambda 19: NotifySuccess (completion_notifier)**

**Time: T+49 seconds**

**Purpose:** Send success notification to Slack

**Input:**
```json
{
  "execution_id": "abc123-def456",
  "status": "SUCCEEDED",
  "slack_channel": "C0123456789",
  "slack_user": "U0987654321",
  "project_name": "EMS Platform",
  "result": { /* all results */ }
}
```

**Lambda Execution:**
```python
# File: lambda_functions/completion_notifier/handler.py

def lambda_handler(event, context):
    from slack_sdk import WebClient
    
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    client = WebClient(token=slack_token)
    
    # Build success message
    message = {
        "text": "🎉 Onboarding completed for EMS Platform",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🎉 Onboarding Complete: EMS Platform"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Requested by: <@U0987654321>\nExecution ID: `abc123-def456`"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "✅ Project: *EMS-PLATFORM*\n✅ HCP Project ID: `prj-abc123xyz789`\n✅ GitHub Branch: `ems-platform`\n✅ GitHub File: https://github.com/adityajhacse/test/blob/ems-platform/requests/ems-platform-dev.json\n✅ Workspaces Created: ems-platform-dev, ems-platform-qa, ems-platform-prod"
                }
            }
        ]
    }
    
    # Send to Slack
    response = client.chat_postMessage(
        channel="C0123456789",
        text=message["text"],
        blocks=message["blocks"]
    )
    
    return {
        "statusCode": 200,
        "notified": True,
        "message_ts": response["ts"]
    }
```

**Slack API Call:**
```http
POST https://slack.com/api/chat.postMessage
Authorization: Bearer xoxb-4909201991235...
Content-Type: application/json

Body: {
  "channel": "C0123456789",
  "text": "🎉 Onboarding completed for EMS Platform",
  "blocks": [ /* formatted blocks */ ]
}

Response: 200 OK
{
  "ok": true,
  "ts": "1717582818.123456"
}
```

**User Sees in Slack:**
```
┌──────────────────────────────────────────────────┐
│ 🎉 Onboarding Complete: EMS Platform            │
├──────────────────────────────────────────────────┤
│                                                  │
│ Requested by: @john.doe                         │
│ Execution ID: `abc123-def456`                   │
│                                                  │
│ ✅ Project: *EMS-PLATFORM*                      │
│ ✅ HCP Project ID: `prj-abc123xyz789`           │
│ ✅ GitHub Branch: `ems-platform`                │
│ ✅ GitHub File: https://github.com/...          │
│ ✅ Workspaces Created: ems-platform-dev,        │
│    ems-platform-qa, ems-platform-prod           │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## ⏱️ Complete Timeline Summary

| Time | Step | Lambda | Duration | What Happened |
|------|------|--------|----------|---------------|
| T+0s | User types command | - | - | `/aws-det-poc` in Slack |
| T+0s | Modal opens | - | - | User sees form |
| T+30s | User submits | - | - | Form data collected |
| T+31s | API Gateway | - | 0.1s | Receives request |
| T+31s | Step Functions starts | - | 0.1s | Execution begins |
| T+31s | Initialize | status_tracker | 0.3s | Creates DynamoDB record |
| T+32s | Validate | validate_intake | 0.5s | Validates form data |
| T+32s | Track validation | status_tracker | 0.2s | Updates DynamoDB |
| T+33s | Create branch | github_branch | 0.8s | Creates `ems-platform` branch |
| T+33s | Track branch | status_tracker | 0.2s | Updates DynamoDB |
| T+34s | Commit file | github_commit | 0.9s | Creates AFT JSON, commits |
| T+35s | Track commit | status_tracker | 0.2s | Updates DynamoDB |
| T+36s | Create project | hcp_project | 0.9s | Creates HCP project |
| T+37s | Track project | status_tracker | 0.2s | Updates DynamoDB |
| T+38s | Create workspaces | hcp_workspace × 3 | 5.0s | **PARALLEL**: 3 workspaces |
| T+43s | Track workspaces | status_tracker | 0.2s | Updates DynamoDB |
| T+44s | Configure vars | hcp_vars × 3 | 3.0s | **PARALLEL**: 3 configs |
| T+47s | Track vars | status_tracker | 0.2s | Updates DynamoDB |
| T+48s | Mark complete | status_tracker | 0.3s | Final DynamoDB update |
| T+49s | Notify Slack | completion_notifier | 0.5s | Sends success message |
| **T+49s** | **COMPLETE** | - | **~18 seconds** | **User sees notification** |

**Total Execution Time:** ~18 seconds (from API Gateway to Slack notification)

---

## 🎯 What User Can Do Next

### 1. **View GitHub Commit**
Click link in Slack → Opens:
```
https://github.com/adityajhacse/test/blob/ems-platform/requests/ems-platform-dev.json
```

### 2. **View HCP Terraform Project**
Go to: https://app.terraform.io/app/adityajhacse/projects/prj-abc123xyz789

See:
- Project: EMS-PLATFORM
- Workspaces: ems-platform-dev, ems-platform-qa, ems-platform-prod

### 3. **Check Workspace Configuration**
Click any workspace → Settings → Variables

See:
- `TFC_AWS_PROVIDER_AUTH = true`
- `TFC_AWS_RUN_ROLE_ARN = arn:aws:iam::916657620953:role/HCP-terraform-role`

### 4. **Query DynamoDB for Status**
```bash
aws dynamodb get-item \
  --table-name det-onboarding-prod-executions \
  --key '{"execution_id": {"S": "abc123-def456"}}'
```

### 5. **View CloudWatch Logs**
```bash
# Step Functions logs
aws logs tail /aws/states/det-onboarding-prod-onboarding --follow

# Lambda logs
aws logs tail /aws/lambda/det-onboarding-prod-github-commit --follow
```

---

## 🚨 Error Handling Examples

### **Scenario 1: Validation Fails**

If user submits incomplete form:

1. `validate_intake` returns `valid: false`
2. Step Functions goes to `ValidationFailed` state
3. `status_tracker` marks as `FAILED`
4. `completion_notifier` sends failure message:

```
┌──────────────────────────────────────────┐
│ ❌ Onboarding Failed: EMS Platform       │
├──────────────────────────────────────────┤
│ Requested by: @john.doe                 │
│ Execution ID: `abc123-def456`           │
│                                          │
│ Error:                                   │
│ ```                                      │
│ Missing required fields:                 │
│ - team_dl (team email required)         │
│ ```                                      │
│                                          │
│ Check AWS Step Functions console for    │
│ detailed execution history.              │
└──────────────────────────────────────────┘
```

### **Scenario 2: GitHub API Rate Limit**

If GitHub rate limit hit:

1. `github_commit` fails with 429 error
2. Step Functions **RETRIES** (3 attempts with backoff)
3. Retry 2: Succeeds after 6 seconds
4. Workflow continues normally

### **Scenario 3: One Workspace Fails**

If QA workspace creation fails:

1. Dev workspace: ✅ Created
2. QA workspace: ❌ Failed
3. Prod workspace: ✅ Created (continues anyway)
4. Result shows partial success
5. User can fix QA manually

---

## 📊 Monitoring Dashboard View

User can build CloudWatch dashboard showing:

```
┌─────────────────────────────────────────┐
│ DET Onboarding Dashboard                │
├─────────────────────────────────────────┤
│                                         │
│ Total Executions Today: 47              │
│ Successful: 45 (96%)                    │
│ Failed: 2 (4%)                          │
│                                         │
│ Average Duration: 18.3 seconds          │
│                                         │
│ Current Status:                         │
│ ● Running: 3                            │
│ ○ Pending: 0                            │
│                                         │
│ Recent Executions:                      │
│ ✅ abc123 - EMS Platform (18s ago)      │
│ ✅ def456 - CRM Service (2m ago)        │
│ ❌ ghi789 - Failed validation (5m ago)  │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🎉 Summary

**Complete Journey:**
1. User types `/aws-det-poc` → **0 seconds**
2. Fills form → **30 seconds**
3. Submits → **31 seconds**
4. Workflow executes (8 Lambda functions, some parallel) → **31-49 seconds**
5. Slack notification received → **49 seconds**
6. User clicks links to see results → **Done!**

**Total time:** ~50 seconds from start to notification
**Lambda executions:** 19 total (6 workflow + 13 tracking/notifications)
**APIs called:** GitHub (5 calls), HCP Terraform (7 calls), Slack (2 calls)
**Results:** GitHub branch ✅, AFT JSON ✅, HCP Project ✅, 3 Workspaces ✅, Variables configured ✅

Everything tracked in DynamoDB with complete audit trail! 🚀
