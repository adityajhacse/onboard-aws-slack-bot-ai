# 🚀 MASTER DEPLOYMENT CHECKLIST

## Overview

Three critical fixes ready to deploy:

1. **Status Tracking Fix** - Real-time step status updates
2. **Duplicate Detection** - Prevent duplicate project names
3. **Validation-First** - Create records only after validation succeeds

---

## 📦 All Files Ready

### Lambda Functions (9 total)

| Function | Fixes | Size | File |
|----------|-------|------|------|
| `validate_intake` | Duplicate checking | 9.7KB | `validate_intake/validate_intake.zip` |
| `github_branch` | Status tracking + keywords | 9.9KB | `github_branch/github_branch.zip` |
| `github_commit` | Status tracking + keywords | 10KB | `github_commit/github_commit.zip` |
| `hcp_project` | Status tracking + keywords | 7.8KB | `hcp_project/hcp_project.zip` |
| `hcp_workspace` | Status tracking + keywords | 7.9KB | `hcp_workspace/hcp_workspace.zip` |
| `completion_notifier` | Keywords + validation errors | 6.2KB | `completion_notifier/completion_notifier.zip` |
| `status_lookup` | Reserved keywords | 5.7KB | `status_lookup/status_lookup.zip` |
| `status_tracker` | Reserved keywords | 5.1KB | `status_tracker/status_tracker.zip` |

### Infrastructure

| Component | Changes | How to Deploy |
|-----------|---------|---------------|
| Step Functions | Validation-first flow | Terraform or Console |

---

## 🎯 Deployment Steps

### Step 1: Update Lambda Functions

Go to: https://console.aws.amazon.com/lambda/home?region=us-east-1

Upload each zip file to its function:

- [ ] `det-onboarding-prod-validate-intake` ← **NEW: Duplicate checking**
- [ ] `det-onboarding-prod-github-branch`
- [ ] `det-onboarding-prod-github-commit`
- [ ] `det-onboarding-prod-hcp-project`
- [ ] `det-onboarding-prod-hcp-workspace`
- [ ] `det-onboarding-prod-completion-notifier` ← **UPDATED: Validation errors**
- [ ] `det-onboarding-prod-status-lookup`
- [ ] `det-onboarding-prod-status-tracker`

**For each function:**
1. Click function name
2. Click "Upload from" → ".zip file"
3. Select the zip file from `terraform/modules/lambda/lambda_functions/[name]/[name].zip`
4. Click "Save"
5. Wait for "Successfully updated" message

### Step 2: Update Step Functions

**Option A: Terraform (Recommended)**
```bash
cd terraform
terraform apply -auto-approve
```

**Option B: AWS Console**
1. Go to: https://console.aws.amazon.com/states/home?region=us-east-1
2. Click on: `det-onboarding-prod`
3. Click "Edit"
4. Update the state machine definition
5. Click "Save"

---

## ✅ What Each Fix Does

### Fix 1: Status Tracking (8 Lambdas)

**Problem:** Steps stuck at `RUNNING` or `PENDING`

**Fix:** 
- Lambda functions now update their status in real-time
- Fixed variable scope bug (`db` not accessible)
- Fixed DynamoDB reserved keywords (`result`, `error`, `status`)

**Result:**
```
✅ Validate Intake - SUCCEEDED
✅ Create GitHub Branch - SUCCEEDED
✅ Commit to GitHub - SUCCEEDED
✅ Create HCP Project - SUCCEEDED
✅ Create Workspaces - SUCCEEDED
✅ Configure Variables - SUCCEEDED
```

### Fix 2: Duplicate Detection (validate_intake)

**Problem:** Users could create multiple requests for same project

**Fix:**
- Check for existing SUCCEEDED/RUNNING requests
- Block duplicates with clear error message
- Allow retrying FAILED requests

**Result:**
```
❌ Onboarding Failed: Dev204

Error:
• Onboarding request already exists for project 'Dev204'
  Service Request ID: SR-20260608-1234, Status: SUCCEEDED

💡 Check existing request: /aws-det-onboard-status SR-20260608-1234
```

### Fix 3: Validation-First (Step Functions + completion_notifier)

**Problem:** 
- DynamoDB records created BEFORE validation
- Database polluted with invalid/duplicate requests
- JSONPath error when validation failed

**Fix:**
- Validate FIRST, create record AFTER
- Only create DynamoDB records for valid requests
- Handle validation errors properly

**Result:**
- Clean database (no invalid records)
- No duplicate records created
- Clear validation error messages

---

## 🧪 Testing Checklist

After deployment, test each feature:

### Test 1: Status Tracking

- [ ] Start new onboarding request
- [ ] Get Service Request ID: `SR-YYYYMMDD-XXXX`
- [ ] Check status: `/aws-det-onboard-status SR-YYYYMMDD-XXXX`
- [ ] **Verify:** All steps show `SUCCEEDED` (not `RUNNING` or `PENDING`)

### Test 2: Duplicate Detection

- [ ] Submit onboarding for project "TestDup123"
- [ ] Wait for it to complete successfully
- [ ] Submit onboarding for project "TestDup123" again
- [ ] **Verify:** Second request is blocked with error message
- [ ] **Verify:** Error shows first Service Request ID
- [ ] **Verify:** Only ONE record in DynamoDB for "TestDup123"

### Test 3: Validation-First

- [ ] Submit onboarding request (valid or invalid)
- [ ] Check DynamoDB immediately
- [ ] **If validation fails:** Verify NO record was created
- [ ] **If validation succeeds:** Verify record WAS created with SR ID

### Test 4: Error Messages

- [ ] Trigger validation failure (duplicate project name)
- [ ] **Verify:** User receives Slack notification
- [ ] **Verify:** Error message is clear and actionable
- [ ] **Verify:** No JSONPath errors in Step Functions logs

---

## 📊 Before vs After

### Before Deployment

**Status Tracking:**
```
✅ Status: SUCCEEDED
⏳ Validate Intake - PENDING         ← Wrong!
🔄 Create GitHub Branch - RUNNING    ← Stuck!
🔄 Commit to GitHub - RUNNING        ← Stuck!
```

**Duplicate Handling:**
```
DynamoDB: 2 records for same project  ← Pollution!
User: No warning about duplicate      ← Confusion!
```

**Validation:**
```
Step 1: Create record
Step 2: Validate (fails)
Result: Invalid record in database    ← Pollution!
```

### After Deployment

**Status Tracking:**
```
✅ Status: SUCCEEDED
✅ Validate Intake - SUCCEEDED        ← Correct!
✅ Create GitHub Branch - SUCCEEDED   ← Fixed!
✅ Commit to GitHub - SUCCEEDED       ← Fixed!
```

**Duplicate Handling:**
```
DynamoDB: 1 record for project        ← Clean!
User: Clear error with SR ID          ← Helpful!
```

**Validation:**
```
Step 1: Validate
Step 2: Create record (only if valid)
Result: Clean database                ← Fixed!
```

---

## 🔍 Verification

### Check CloudWatch Logs

**validate_intake:**
```
/aws/lambda/det-onboarding-prod-validate-intake
```
Look for: `Found duplicate request` or `No existing requests found`

**github_branch:**
```
/aws/lambda/det-onboarding-prod-github-branch
```
Look for: `Updated step CreateGitHubBranch status to SUCCEEDED`

**Step Functions:**
```
/aws/vendedlogs/states/det-onboarding-prod
```
Look for: Validation running before InitializeTracking

### Check DynamoDB

```bash
# Count records for a project
aws dynamodb query \
  --table-name det-onboarding-prod-executions \
  --index-name project-name-index \
  --key-condition-expression "project_name = :name" \
  --expression-attribute-values '{":name":{"S":"TestDup123"}}' \
  --select COUNT
```

Should return: `Count: 1` (not 2 or more)

---

## 🚨 Rollback Plan

If issues occur:

### Rollback Lambdas

For each Lambda, use "Versions" tab to rollback:
1. Go to function → "Versions"
2. Find previous version
3. Click "Actions" → "Publish new version from this version"

### Rollback Step Functions

```bash
cd terraform
git checkout HEAD~1 modules/step_functions/state_machine.json.tpl
terraform apply
```

---

## 📝 Documentation

**Detailed docs created:**
- `DEPLOY_ALL_FIXES.md` - Status tracking + reserved keywords
- `DUPLICATE_CHECK_FEATURE.md` - Duplicate detection
- `VALIDATION_FIRST_FIX.md` - Validation-first workflow

---

## ✨ Summary

### Bugs Fixed

1. ✅ Status tracking stuck at RUNNING
2. ✅ DynamoDB reserved keyword errors
3. ✅ Variable scope issue (db not defined)
4. ✅ Duplicate project names allowed
5. ✅ Records created before validation
6. ✅ JSONPath error on validation failure

### Features Added

1. ✅ Real-time step status updates
2. ✅ Duplicate project name detection
3. ✅ Clean database (no invalid records)
4. ✅ Better error messages for users

### Files Updated

- **8 Lambda functions** (all `.zip` files ready)
- **1 Step Functions state machine** (via Terraform)

---

## 🎯 Success Criteria

After deployment, you should see:

- ✅ All steps show correct status (`SUCCEEDED`, not `RUNNING`)
- ✅ Duplicate requests are blocked with clear error
- ✅ Only valid requests create DynamoDB records
- ✅ No JSONPath errors in Step Functions logs
- ✅ No `NameError: db is not defined` in Lambda logs
- ✅ No `ValidationException: reserved keyword` errors

**All fixes are ready - deploy now!** 🚀

---

## 💡 Tips

1. **Deploy in order:** Lambdas first, then Step Functions
2. **Test after each:** Verify Lambdas work before updating Step Functions
3. **Check logs:** Monitor CloudWatch during first test run
4. **Keep old versions:** AWS Lambda automatically versions on each update
5. **Document issues:** Note any problems for quick rollback

**Deployment time:** ~15 minutes for all updates
**Testing time:** ~10 minutes per test case
**Total time:** ~45 minutes
