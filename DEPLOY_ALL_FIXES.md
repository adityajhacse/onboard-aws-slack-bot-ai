# 🚨 DEPLOY ALL FIXES - Complete Guide

## Two Critical Bugs Fixed

### Bug 1: Variable Scope Issue ✅
Lambda functions were stuck at `RUNNING` because `db` variable was scoped inside a try block.

### Bug 2: DynamoDB Reserved Keyword ✅
```
ValidationException: Attribute name is a reserved keyword; reserved keyword: result
```

Fixed by using `ExpressionAttributeNames` to alias reserved keywords (`result`, `error`, `status`).

---

## 📦 All Deployment Packages Ready

Seven Lambda functions need to be updated:

```
terraform/modules/lambda/lambda_functions/
├── github_branch/github_branch.zip (9.9KB)        ← Status tracking
├── github_commit/github_commit.zip (10KB)         ← Status tracking
├── hcp_project/hcp_project.zip (7.8KB)            ← Status tracking
├── hcp_workspace/hcp_workspace.zip (7.9KB)        ← Status tracking
├── completion_notifier/completion_notifier.zip (6.0KB)  ← Uses dynamodb_helper
├── status_lookup/status_lookup.zip (5.7KB)        ← Uses dynamodb_helper
└── status_tracker/status_tracker.zip (5.1KB)      ← Uses dynamodb_helper
```

---

## 🚀 Deploy via AWS Console

### Step-by-Step Instructions

1. **Open AWS Lambda Console**
   https://console.aws.amazon.com/lambda/home?region=us-east-1

2. **Upload Each Function**

   For each function below:
   - Click the function name
   - Click "Upload from" → ".zip file"
   - Select the corresponding zip file
   - Click "Save"
   - Wait for "Successfully updated" message

   **Functions to update:**

   | Function Name | Zip File Location |
   |--------------|-------------------|
   | `det-onboarding-prod-github-branch` | `github_branch/github_branch.zip` |
   | `det-onboarding-prod-github-commit` | `github_commit/github_commit.zip` |
   | `det-onboarding-prod-hcp-project` | `hcp_project/hcp_project.zip` |
   | `det-onboarding-prod-hcp-workspace` | `hcp_workspace/hcp_workspace.zip` |
   | `det-onboarding-prod-completion-notifier` | `completion_notifier/completion_notifier.zip` |
   | `det-onboarding-prod-status-lookup` | `status_lookup/status_lookup.zip` |
   | `det-onboarding-prod-status-tracker` | `status_tracker/status_tracker.zip` |

---

## ✅ What Was Fixed

### Fix 1: Variable Scope (All Status Tracking Lambdas)

**Before (BROKEN):**
```python
if execution_id:
    try:
        db = get_helper()  # ❌ Only exists in this try block
        db.update_step_status(execution_id, "Step", "RUNNING")
    except Exception as e:
        pass

# Later in the function...
if execution_id:
    try:
        db.update_step_status(execution_id, "Step", "SUCCEEDED")  # ❌ NameError!
    except Exception as e:
        pass
```

**After (FIXED):**
```python
# Get helper once at function level
db = get_helper() if execution_id else None

if db:
    try:
        db.update_step_status(execution_id, "Step", "RUNNING")
    except Exception as e:
        pass

# Later...
if db:  # ✅ db is defined!
    try:
        db.update_step_status(execution_id, "Step", "SUCCEEDED")
    except Exception as e:
        pass
```

---

### Fix 2: DynamoDB Reserved Keywords (dynamodb_helper.py)

**Before (BROKEN):**
```python
if result:
    update_expression.append(f'steps.{step_name}.result = :result')  # ❌ 'result' is reserved
    expression_values[':result'] = result

if error:
    update_expression.append(f'steps.{step_name}.error = :error')  # ❌ 'error' is reserved
    expression_values[':error'] = error
```

**After (FIXED):**
```python
if result:
    update_expression.append(f'steps.{step_name}.#result = :result')  # ✅ Using alias
    expression_values[':result'] = result
    expression_names['#result'] = 'result'  # ✅ Map #result → result

if error:
    update_expression.append(f'steps.{step_name}.#error = :error')  # ✅ Using alias
    expression_values[':error'] = error
    expression_names['#error'] = 'error'  # ✅ Map #error → error
```

---

## 🧪 Test After Deployment

### 1. Start New Onboarding
```
/aws-det-onboard
```

### 2. Get Service Request ID
Look for: `SR-20260608-XXXX`

### 3. Check Status
```
/aws-det-onboard-status SR-20260608-XXXX
```

### 4. Expected Result ✅

```
🎫 Service Request Status

🎫 Request ID: SR-20260608-XXXX
📦 Project: Dev200
✅ Status: SUCCEEDED
⏱️ Time: Completed in 13 seconds

Pipeline Steps:
✅ Validate Intake - SUCCEEDED
✅ Create GitHub Branch - SUCCEEDED      ← Fixed: Was stuck at RUNNING
✅ Commit to GitHub - SUCCEEDED          ← Fixed: Was stuck at RUNNING
✅ Create HCP Project - SUCCEEDED        ← Fixed: Was stuck at RUNNING
✅ Create Workspaces - SUCCEEDED
✅ Configure Variables - SUCCEEDED
```

**All steps should show SUCCEEDED!** 🎯

---

## 🔍 Verify Deployment

### Check Lambda Last Modified Time

```bash
# Check if functions were updated
aws lambda get-function \
  --function-name det-onboarding-prod-github-branch \
  --query 'Configuration.LastModified' \
  --output text
```

Should show recent timestamp (today).

### Check CloudWatch Logs

After running a test onboarding, check logs for errors:

```
AWS Console → CloudWatch → Log Groups
→ /aws/lambda/det-onboarding-prod-github-branch
```

**Should NOT see:**
- ❌ `NameError: name 'db' is not defined`
- ❌ `ValidationException: reserved keyword: result`

**Should see:**
- ✅ `Updated step CreateGitHubBranch status to RUNNING`
- ✅ `Updated step CreateGitHubBranch status to SUCCEEDED`

---

## 📋 Deployment Checklist

- [ ] Upload `github_branch/github_branch.zip` → `det-onboarding-prod-github-branch`
- [ ] Upload `github_commit/github_commit.zip` → `det-onboarding-prod-github-commit`
- [ ] Upload `hcp_project/hcp_project.zip` → `det-onboarding-prod-hcp-project`
- [ ] Upload `hcp_workspace/hcp_workspace.zip` → `det-onboarding-prod-hcp-workspace`
- [ ] Upload `completion_notifier/completion_notifier.zip` → `det-onboarding-prod-completion-notifier`
- [ ] Upload `status_lookup/status_lookup.zip` → `det-onboarding-prod-status-lookup`
- [ ] Upload `status_tracker/status_tracker.zip` → `det-onboarding-prod-status-tracker`
- [ ] Start new onboarding request
- [ ] Check status shows SUCCEEDED for all steps
- [ ] Verify no errors in CloudWatch Logs

---

## 🐛 Still Having Issues?

### Issue: Status still shows RUNNING

**Check:**
1. Did you upload ALL 7 Lambda functions?
2. Check CloudWatch Logs for the specific Lambda that's stuck
3. Look for the error message

**Common errors:**
- `NameError: name 'db' is not defined` → Lambda not updated with new code
- `ValidationException: reserved keyword` → Lambda not updated with fixed dynamodb_helper.py

### Issue: Different error

Check CloudWatch Logs for:
```
/aws/lambda/det-onboarding-prod-[function-name]
```

Share the error message for further debugging.

---

## 📝 Summary

**Two critical bugs fixed:**
1. ✅ Variable scope issue (db not accessible)
2. ✅ DynamoDB reserved keyword issue (result, error, status)

**Seven Lambda functions updated:**
- github_branch, github_commit, hcp_project, hcp_workspace (status tracking)
- completion_notifier, status_lookup, status_tracker (use dynamodb_helper)

**All deployment packages are ready in:**
```
terraform/modules/lambda/lambda_functions/*/[name].zip
```

**Deploy them via AWS Console now!** 🚀
