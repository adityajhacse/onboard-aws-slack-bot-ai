# 🚨 URGENT: Deploy Status Tracking Fix

## Problem
Lambda functions are stuck at `RUNNING` status because of a variable scope bug. The fix is ready but needs deployment.

## Quick Deploy (Choose One Method)

### Method 1: Terraform (Recommended if working)

```bash
cd terraform

# Clean Terraform providers
rm -rf .terraform .terraform.lock.hcl

# Reinitialize
terraform init

# Deploy
terraform taint module.lambda.aws_lambda_layer_version.shared_layer
terraform apply -auto-approve
```

---

### Method 2: AWS Console (Manual)

For each Lambda function, create a deployment package and upload:

#### Step 1: Create Deployment Packages

```bash
cd terraform/modules/lambda/lambda_functions

# Package github_branch
cd github_branch
cp ../shared_layer/python/*.py .
zip github_branch.zip handler.py *.py
cd ..

# Package github_commit  
cd github_commit
cp ../shared_layer/python/*.py .
zip github_commit.zip handler.py *.py
cd ..

# Package hcp_project
cd hcp_project
cp ../shared_layer/python/*.py .
zip hcp_project.zip handler.py *.py hcp_terraform.py
cd ..

# Package hcp_workspace
cd hcp_workspace
cp ../shared_layer/python/*.py .
zip hcp_workspace.zip handler.py *.py hcp_terraform.py
cd ..
```

#### Step 2: Upload via AWS Console

1. Go to AWS Lambda Console: https://console.aws.amazon.com/lambda
2. For each function:
   - **det-onboarding-prod-github-branch**
     - Click "Upload from" → ".zip file"
     - Upload `github_branch/github_branch.zip`
     - Click "Save"
   
   - **det-onboarding-prod-github-commit**
     - Upload `github_commit/github_commit.zip`
   
   - **det-onboarding-prod-hcp-project**
     - Upload `hcp_project/hcp_project.zip`
   
   - **det-onboarding-prod-hcp-workspace**
     - Upload `hcp_workspace/hcp_workspace.zip`

---

### Method 3: AWS CLI (If configured)

```bash
cd terraform/modules/lambda/lambda_functions

# Deploy github_branch
cd github_branch
cp ../shared_layer/python/*.py .
zip github_branch.zip handler.py *.py
aws lambda update-function-code \
  --function-name det-onboarding-prod-github-branch \
  --zip-file fileb://github_branch.zip \
  --region us-east-1
cd ..

# Deploy github_commit
cd github_commit
cp ../shared_layer/python/*.py .
zip github_commit.zip handler.py *.py
aws lambda update-function-code \
  --function-name det-onboarding-prod-github-commit \
  --zip-file fileb://github_commit.zip \
  --region us-east-1
cd ..

# Deploy hcp_project
cd hcp_project
cp ../shared_layer/python/*.py .
zip hcp_project.zip handler.py *.py hcp_terraform.py
aws lambda update-function-code \
  --function-name det-onboarding-prod-hcp-project \
  --zip-file fileb://hcp_project.zip \
  --region us-east-1
cd ..

# Deploy hcp_workspace
cd hcp_workspace
cp ../shared_layer/python/*.py .
zip hcp_workspace.zip handler.py *.py hcp_terraform.py
aws lambda update-function-code \
  --function-name det-onboarding-prod-hcp-workspace \
  --zip-file fileb://hcp_workspace.zip \
  --region us-east-1
cd ..

echo "✅ All functions deployed!"
```

---

## What Was Fixed

### The Bug (Variable Scope Issue)

```python
# BEFORE (BROKEN):
if execution_id:
    try:
        db = get_helper()  # ❌ db only exists inside this try block
        db.update_step_status(execution_id, "Step", "RUNNING")
    except Exception as e:
        pass

# Later in the same function...
if execution_id:
    try:
        db.update_step_status(...)  # ❌ NameError: db is not defined!
    except Exception as e:
        pass
```

**Result:** Function updates to `RUNNING` but crashes when trying to update to `SUCCEEDED`.

### The Fix

```python
# AFTER (FIXED):
execution_id = event.get("execution_id") or ""
if execution_id and ":execution:" in execution_id:
    execution_id = execution_id.split(":")[-1]

# Get DynamoDB helper ONCE at function level
db = get_helper() if execution_id else None

# Update to RUNNING
if db:
    try:
        db.update_step_status(execution_id, "Step", "RUNNING")
    except Exception as e:
        pass

# Later... update to SUCCEEDED
if db:  # ✅ db is defined and accessible!
    try:
        db.update_step_status(execution_id, "Step", "SUCCEEDED", result={...})
    except Exception as e:
        pass
```

**Result:** Function properly updates from `RUNNING` → `SUCCEEDED`.

---

## After Deployment

### Test It

1. Start a new onboarding request: `/aws-det-onboard`
2. Get the Service Request ID: `SR-20260608-XXXX`
3. Check status: `/aws-det-onboard-status SR-20260608-XXXX`

### Expected Result ✅

```
🎫 Service Request Status

🎫 Request ID: SR-20260608-XXXX
📦 Project: Dev200
✅ Status: SUCCEEDED
⏱️ Time: Completed in 13 seconds

Pipeline Steps:
✅ Validate Intake - SUCCEEDED
✅ Create GitHub Branch - SUCCEEDED
✅ Commit to GitHub - SUCCEEDED
✅ Create HCP Project - SUCCEEDED
✅ Create Workspaces - SUCCEEDED
✅ Configure Variables - SUCCEEDED
```

**All steps will now show `SUCCEEDED` instead of stuck at `RUNNING`!** 🎯

---

## Files That Were Fixed

1. `terraform/modules/lambda/lambda_functions/github_branch/handler.py`
2. `terraform/modules/lambda/lambda_functions/github_commit/handler.py`
3. `terraform/modules/lambda/lambda_functions/hcp_project/handler.py`
4. `terraform/modules/lambda/lambda_functions/hcp_workspace/handler.py`

All 4 files had the same bug - `db` variable was scoped inside a try block and not accessible later.

---

## Still Not Working?

If deployment succeeds but status still shows `RUNNING`:

1. **Check CloudWatch Logs** for each Lambda:
   ```
   AWS Console → CloudWatch → Log Groups → /aws/lambda/det-onboarding-prod-github-branch
   ```
   Look for errors like `NameError: name 'db' is not defined`

2. **Verify Lambda Updated:**
   ```bash
   aws lambda get-function --function-name det-onboarding-prod-github-branch | jq .Configuration.LastModified
   ```
   Should show recent timestamp.

3. **Check Execution ID is Passed:**
   In CloudWatch logs, look for:
   ```
   execution_id: arn:aws:states:us-east-1:...
   ```
   If it's `None` or missing, the Step Functions isn't passing it correctly.

---

**Deploy ASAP to fix the stuck `RUNNING` status issue!** 🚀
