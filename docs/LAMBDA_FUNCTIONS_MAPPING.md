# Lambda Functions - What Each One Does

## Complete Function Mapping

### 1. **validate_intake** Lambda
**What it does:**
- ✅ Validates all form fields (required fields, allowed values)
- ✅ Normalizes intake data (project name → slug, etc.)
- ✅ Returns validation errors if any

**Code location:**
- Handler: `lambda_functions/validate_intake/handler.py`
- Shared: `lambda_functions/shared_layer/python/det_intake.py`

**Key functions called:**
- `validate_intake()` - Full validation
- `normalize_intake()` - Data normalization

---

### 2. **github_branch** Lambda
**What it does:**
- ✅ Creates Git branch in GitHub repository
- ✅ Branch name from project name (e.g., "ems-project")
- ✅ Creates from base branch (main/master)
- ✅ Idempotent (doesn't fail if branch exists)

**Code location:**
- Handler: `lambda_functions/github_branch/handler.py`
- Shared: `lambda_functions/shared_layer/python/github_api.py`

**Key functions called:**
- `sanitize_git_branch_from_project_name()` - Clean branch name
- `ensure_git_branch()` - Create branch via GitHub API

---

### 3. **github_commit** Lambda
**What it does:**
- ✅ **CREATES AFT JSON FILE** with intake data
- ✅ Commits JSON to GitHub repository
- ✅ File path: `requests/<project-slug>-<env>.json`
- ✅ Returns commit SHA and file URL

**Code location:**
- Handler: `lambda_functions/github_commit/handler.py`
- Shared: `lambda_functions/shared_layer/python/github_api.py`

**Key functions called:**
- `build_github_intake_document()` - **Creates AFT JSON payload**
- `put_repository_json_file()` - Commits to GitHub

**AFT JSON Structure Created:**
```json
{
  "request_id": "ems-dev",
  "aft": {
    "control_tower_parameters": {
      "AccountEmail": "det-aws-platform-e2e-dev@salesforce.com",
      "AccountName": "EMS Dev",
      "ManagedOrganizationalUnit": "Dev (ou-...)",
      "SSOUserEmail": "user@example.com",
      "SSOUserFirstName": "First",
      "SSOUserLastName": "Last"
    },
    "custom_fields": {
      "github_actions_subject_patterns": [...],
      "enable_private_dns_rfc": true,
      "project_name": "ems",
      "terraform_cloud_project": "EMS",
      "region": "us-east-1",
      "vpc_size": "small"
    },
    "change_management_parameters": {
      "change_requested_by": "User Name",
      "change_reason": "Business justification text"
    }
  }
}
```

---

### 4. **hcp_project** Lambda
**What it does:**
- ✅ **CREATES HCP TERRAFORM PROJECT**
- ✅ Project name from intake (uppercase)
- ✅ Returns project ID for workspace creation

**Code location:**
- Handler: `lambda_functions/hcp_project/handler.py`
- Shared: `lambda_functions/shared_layer/python/hcp_terraform.py`

**Key functions called:**
- `_hcp_config()` - Get HCP credentials
- `_create_project()` - **Creates project via HCP API**

**What gets created:**
- HCP Terraform Project (e.g., "EMS", "PLATFORM-API")
- Project ID returned (e.g., "prj-abc123...")

---

### 5. **hcp_workspace** Lambda (Runs in PARALLEL)
**What it does:**
- ✅ **CREATES HCP TERRAFORM WORKSPACE** for ONE environment
- ✅ Links workspace to GitHub repository
- ✅ Sets VCS branch (dev/qa/prod)
- ✅ Auto-creates branch if missing

**Code location:**
- Handler: `lambda_functions/hcp_workspace/handler.py`
- Shared: `lambda_functions/shared_layer/python/hcp_terraform.py`

**Key functions called:**
- `_resolve_workspace_name()` - Determine workspace name
- `_create_workspace()` - **Creates workspace via HCP API**
- `_ensure_workspace_branch()` - Create branch if needed

**Parallel execution example:**
```
Dev workspace   → Creates "ems-dev"   in parallel
QA workspace    → Creates "ems-qa"    in parallel
Prod workspace  → Creates "ems-prod"  in parallel
```

---

### 6. **hcp_vars** Lambda (Runs in PARALLEL)
**What it does:**
- ✅ Configures environment variables for ONE workspace
- ✅ Sets AWS authentication variables
- ✅ Sets IAM role ARN

**Code location:**
- Handler: `lambda_functions/hcp_vars/handler.py`
- Shared: `lambda_functions/shared_layer/python/hcp_terraform.py`

**Key functions called:**
- `_set_workspace_env_vars()` - Configure variables
- `_create_workspace_var()` - Create each variable

**Variables set:**
- `TFC_AWS_PROVIDER_AUTH = true`
- `TFC_AWS_RUN_ROLE_ARN = arn:aws:iam::...`

---

### 7. **status_tracker** Lambda
**What it does:**
- ✅ **Writes status to DynamoDB**
- ✅ Tracks each step execution
- ✅ Stores intake data, results, errors
- ✅ Creates audit logs

**Code location:**
- Handler: `lambda_functions/status_tracker/handler.py`
- Shared: `lambda_functions/shared_layer/python/dynamodb_helper.py`

**Actions:**
- `start` - Create initial record
- `step_update` - Update step status
- `complete` - Mark as succeeded
- `fail` - Mark as failed

---

### 8. **completion_notifier** Lambda
**What it does:**
- ✅ **Sends Slack notifications**
- ✅ Success message with project links
- ✅ Failure message with error details

**Code location:**
- Handler: `lambda_functions/completion_notifier/handler.py`

**Slack messages include:**
- Project name and execution ID
- GitHub file URL
- HCP project ID
- Workspace names
- Error messages (if failed)

---

## Complete Workflow Mapping

```
User submits Slack form
    ↓
API Gateway triggers Step Functions
    ↓
┌─────────────────────────────────────────────────────┐
│ Step Functions Orchestration                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. status_tracker (start)                         │
│     → Creates DynamoDB record                      │
│                                                     │
│  2. validate_intake                                │
│     → Validates form fields                        │
│     → Normalizes data                              │
│                                                     │
│  3. github_branch                                  │
│     → Creates Git branch "ems-project"             │
│                                                     │
│  4. github_commit                                  │
│     → CREATES AFT JSON FILE                        │
│     → Commits to requests/ems-dev.json            │
│                                                     │
│  5. hcp_project                                    │
│     → CREATES HCP TERRAFORM PROJECT "EMS"          │
│                                                     │
│  6. hcp_workspace (parallel × 3)                   │
│     → CREATES WORKSPACE "ems-dev"                  │
│     → CREATES WORKSPACE "ems-qa"                   │
│     → CREATES WORKSPACE "ems-prod"                 │
│                                                     │
│  7. hcp_vars (parallel × 3)                        │
│     → Configures ems-dev variables                 │
│     → Configures ems-qa variables                  │
│     → Configures ems-prod variables                │
│                                                     │
│  8. status_tracker (complete)                      │
│     → Updates DynamoDB: SUCCEEDED                  │
│                                                     │
│  9. completion_notifier                            │
│     → Sends Slack success message                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Shared Layer Contents

The `shared_layer/python/` contains all the actual implementation:

### github_api.py (15.6 KB)
```python
def build_github_intake_document()  # Creates AFT JSON
def put_repository_json_file()      # Commits to GitHub
def ensure_git_branch()              # Creates branch
def sanitize_git_branch_from_project_name()  # Clean name
# ... 30+ more functions
```

### hcp_terraform.py (10.2 KB)
```python
def _create_project()                # Creates HCP project
def _create_workspace()              # Creates workspace
def _set_workspace_env_vars()        # Configures variables
def _ensure_workspace_branch()       # Auto-create branch
# ... 20+ more functions
```

### det_intake.py (15.7 KB)
```python
def validate_intake()                # Full validation
def normalize_intake()               # Data normalization
def preview_request()                # Preview generation
# ... 25+ more functions
```

### dynamodb_helper.py (13.4 KB)
```python
def create_execution_record()        # Initial record
def update_step_status()             # Track steps
def update_execution_status()        # Final status
def get_execution()                  # Query by ID
# ... 15+ more functions
```

## Summary

**YES, all the functionality IS implemented:**

✅ **AFT JSON Creation**: `github_commit` Lambda → `build_github_intake_document()`
✅ **GitHub Commit**: `github_commit` Lambda → `put_repository_json_file()`
✅ **HCP Project Creation**: `hcp_project` Lambda → `_create_project()`
✅ **HCP Workspace Creation**: `hcp_workspace` Lambda → `_create_workspace()`
✅ **Status Tracking**: `status_tracker` Lambda → DynamoDB operations
✅ **Slack Notifications**: `completion_notifier` Lambda → Slack SDK

The Lambda handlers are lightweight wrappers that:
1. Parse the event
2. Call the shared layer functions
3. Handle errors and return results

All the actual business logic is in the shared layer that gets copied from your original `src/` files.
