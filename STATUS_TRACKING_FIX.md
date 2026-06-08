# Status Tracking Fix - Real-Time Step Updates

## Problem
The `/aws-det-onboard-status` command was showing all steps as `PENDING` even after the workflow succeeded:

```
✅ Status: SUCCEEDED
⏳ Validate Intake - PENDING
⏳ Create GitHub Branch - PENDING  
⏳ Commit to GitHub - PENDING
⏳ Create HCP Project - PENDING
⏳ Create Workspaces - PENDING
⏳ Configure Variables - PENDING
```

**Root Cause:** Individual Lambda functions were NOT updating their step status in DynamoDB as they executed.

---

## Solution

### 1. Updated All Lambda Functions

Each Lambda function now tracks its own execution status:

#### **github_branch** (`CreateGitHubBranch` step)
- ✅ Updates status to `RUNNING` when it starts
- ✅ Updates status to `SUCCEEDED` with branch info when done
- ✅ Updates status to `FAILED` with error message on failure

#### **github_commit** (`CommitToGitHub` step)
- ✅ Updates status to `RUNNING` when it starts
- ✅ Updates status to `SUCCEEDED` with commit info when done
- ✅ Updates status to `FAILED` with error message on failure

#### **hcp_project** (`CreateHCPProject` step)
- ✅ Updates status to `RUNNING` when it starts
- ✅ Updates status to `SUCCEEDED` with project info when done
- ✅ Updates status to `FAILED` with error message on failure

#### **hcp_workspace** (runs in parallel for each environment)
- ✅ Records workspace result (success/failure) in DynamoDB
- ✅ Stores workspace_id, workspace_name per environment

#### **hcp_vars** (runs in parallel for each workspace)
- ✅ Runs after workspaces are created
- ✅ No individual tracking (Step Functions tracks overall completion)

---

### 2. Updated Step Functions State Machine

Added status tracking steps after Map states:

#### **TrackWorkspacesSuccess**
- Runs AFTER all workspaces are created (CreateWorkspacesMap completes)
- Updates `CreateWorkspaces` step status to `SUCCEEDED`
- Includes all workspace results

#### **TrackVariablesSuccess**
- Runs AFTER all variables are configured (ConfigureVariablesMap completes)
- Updates `ConfigureVariables` step status to `SUCCEEDED`
- Includes all configuration results

#### **Fixed execution_id Passing**
Added `Parameters` block to each Task to explicitly pass `execution_id`:

```json
{
  "Type": "Task",
  "Resource": "arn:aws:lambda:...",
  "Parameters": {
    "intake.$": "$.intake",
    "slack_channel.$": "$.slack_channel",
    "slack_user.$": "$.slack_user",
    "execution_id.$": "$$.Execution.Name"  // ← THIS WAS MISSING!
  }
}
```

---

### 3. Fixed Null Safety

All Lambda functions now handle `None` execution_id gracefully:

**Before:**
```python
execution_id = event.get("execution_id", "")
if ":execution:" in execution_id:  # ❌ Crashes if None!
    execution_id = execution_id.split(":")[-1]
```

**After:**
```python
execution_id = event.get("execution_id") or ""
if execution_id and ":execution:" in execution_id:  # ✅ Safe!
    execution_id = execution_id.split(":")[-1]
```

---

## Files Changed

### Lambda Functions
1. `terraform/modules/lambda/lambda_functions/github_branch/handler.py`
2. `terraform/modules/lambda/lambda_functions/github_commit/handler.py`
3. `terraform/modules/lambda/lambda_functions/hcp_project/handler.py`
4. `terraform/modules/lambda/lambda_functions/hcp_workspace/handler.py`
5. `terraform/modules/lambda/lambda_functions/hcp_vars/handler.py`

### Infrastructure
6. `terraform/modules/step_functions/state_machine.json.tpl`
   - Added `Parameters` blocks to CreateGitHubBranch, CommitToGitHub, CreateHCPProject
   - Added `TrackWorkspacesSuccess` step
   - Added `TrackVariablesSuccess` step
   - Added `execution_id` to workspace Map parameters

---

## Deployment

### Prerequisites
- Terraform initialized and working
- AWS credentials configured
- Network access to Terraform registry

### Deploy Command
```bash
cd terraform
./deploy_status_tracking.sh
```

Or manually:
```bash
cd terraform
terraform taint module.lambda.aws_lambda_layer_version.shared_layer
terraform apply -auto-approve
```

---

## Testing

### 1. Start a New Onboarding Request
In Slack, use `/aws-det-onboard` to create a new request.

### 2. Get the Service Request ID
The bot will send a notification with:
```
🎫 Service Request ID: SR-20260608-XXXX
```

### 3. Check Status in Real-Time
```
/aws-det-onboard-status SR-20260608-XXXX
```

### Expected Result (After Fix)
```
🎫 Service Request Status

🎫 Request ID: SR-20260608-1408
📦 Project: Dev101
🔄 Status: SUCCEEDED
⏱️ Time: Completed in 6 seconds

Pipeline Steps:
✅ Validate Intake - SUCCEEDED
✅ Create GitHub Branch - SUCCEEDED
✅ Commit to GitHub - SUCCEEDED
✅ Create HCP Project - SUCCEEDED
✅ Create Workspaces - SUCCEEDED
✅ Configure Variables - SUCCEEDED
```

**All steps now show real-time status!** ✅

---

## Error Encountered During Deployment

### Original Error
```
Error: {'Error': 'TypeError', 'Cause': '{"errorMessage": "argument of type \'NoneType\' is not iterable", 
"errorType": "TypeError", "stackTrace": ["  File \\"/var/task/handler.py\\", line 42, in lambda_handler\\n    
if \\":execution:\\" in execution_id\\n"]}'
```

### Cause
1. Step Functions wasn't passing `execution_id` to Lambda functions
2. Lambda functions tried to check `if ":execution:" in execution_id` when `execution_id` was `None`

### Fix
1. ✅ Added null safety: `if execution_id and ":execution:" in execution_id`
2. ✅ Added explicit `Parameters` blocks in Step Functions to pass `execution_id`

---

## Summary

### Before
- ❌ All steps showed `PENDING` even after success
- ❌ No real-time status updates
- ❌ Lambda functions crashed on `None` execution_id

### After
- ✅ Each step updates status in real-time
- ✅ Status lookup shows accurate progress
- ✅ Null-safe error handling
- ✅ Complete execution tracking from start to finish

---

## Architecture

```
User triggers workflow
    ↓
InitializeTracking (creates record with SR ID)
    ↓
ValidateIntake (updates: step_validate_intake = SUCCEEDED)
    ↓
CreateGitHubBranch (updates: step_github_branch = SUCCEEDED)
    ↓
CommitToGitHub (updates: step_github_commit = SUCCEEDED)
    ↓
CreateHCPProject (updates: step_hcp_project = SUCCEEDED)
    ↓
CreateWorkspacesMap (parallel: Dev, QA, Prod)
    ↓ (each workspace records its result)
TrackWorkspacesSuccess (updates: step_workspaces = SUCCEEDED)
    ↓
ConfigureVariablesMap (parallel: configure each workspace)
    ↓
TrackVariablesSuccess (updates: step_variables = SUCCEEDED)
    ↓
TrackCompletion (marks execution as SUCCEEDED)
    ↓
NotifySuccess (sends Slack notification with SR ID)
```

Each step independently updates DynamoDB → Status lookup queries by SR ID → Returns real-time progress! 🎯
