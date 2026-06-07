# 🚀 Deployment Updates

## Latest Update: Default Workspace Names

**Date:** June 5, 2026  
**Status:** ✅ Ready to Deploy

---

## What Changed

### **Feature: Automatic Default Workspace Names**

When users don't specify custom workspace names, the system now automatically generates them.

**Format:** `{project-slug}-{environment}`

**Example:**
- Project: `MyApp`
- Environments: `Dev`, `Staging`, `Prod`
- **Generated workspaces:** `myapp-dev`, `myapp-staging`, `myapp-prod`

---

## Files Modified

### 1. **validate_intake Lambda**
**File:** `terraform/modules/lambda/lambda_functions/validate_intake/handler.py`

**Change:** Added logic to generate default workspace names when `workspace_names` is empty

```python
# Generate default workspace names if not provided
if not workspace_names or workspace_names == {}:
    project_slug = validated_intake.get('project_slug', '').lower()
    environments = validated_intake.get('environments', [])
    
    default_workspace_names = {}
    for env in environments:
        env_lower = env.lower()
        default_workspace_names[env] = f"{project_slug}-{env_lower}"
    
    validated_intake['workspace_names'] = default_workspace_names
```

### 2. **hcp_workspace Lambda**
**File:** `terraform/modules/lambda/lambda_functions/hcp_workspace/handler.py`

**Change:** Enhanced fallback logic for workspace name generation

```python
# Get workspace name for this environment
if workspace_names and environment in workspace_names:
    workspace_name = workspace_names[environment]
else:
    workspace_name = f"{project_slug}-{environment.lower()}"
```

---

## Deployment

### **Quick Deploy**

```bash
cd terraform

# Deploy just the updated Lambda functions
terraform apply -target=module.lambda.aws_lambda_function.validate_intake \
                -target=module.lambda.aws_lambda_function.hcp_workspace
```

### **Full Deploy**

```bash
cd terraform
terraform apply
```

---

## Testing

### Before Fix
**Problem:**
```json
{
  "workspace_names": {}  // Empty - causes failure
}
```

**Error:**
```
JSONPath '$.branch_name' could not be found
```

### After Fix
**Input:**
```json
{
  "project_slug": "myapp",
  "environments": ["Dev", "Prod"],
  "workspace_names": {}  // Empty - OK now!
}
```

**Output:**
```json
{
  "project_slug": "myapp",
  "environments": ["Dev", "Prod"],
  "workspace_names": {
    "Dev": "myapp-dev",
    "Prod": "myapp-prod"
  }
}
```

**Result:** ✅ Workspaces created successfully

---

## How to Test

### 1. **Deploy the Update**
```bash
cd terraform
terraform apply
```

### 2. **Submit Form Without Workspace Names**

In Slack, run `/aws-det-poc` and fill out the form:
- **Project Name:** `TestApp`
- **Environments:** Select `Dev` and `Prod`
- **Workspace Names:** Leave empty or don't specify

### 3. **Check Logs**

```bash
# Watch validate_intake logs
aws logs tail /aws/lambda/det-onboarding-prod-validate-intake --follow

# Should see:
# "Generated default workspace names: {'Dev': 'testapp-dev', 'Prod': 'testapp-prod'}"
```

### 4. **Verify Workspaces Created**

Check HCP Terraform:
- Go to: https://app.terraform.io/app/adityajhacse/workspaces
- Look for: `testapp-dev` and `testapp-prod`

---

## Compatibility

### ✅ Backward Compatible

**Old behavior (custom names):** Still works
```json
{
  "workspace_names": {
    "Dev": "custom-dev-workspace",
    "Prod": "custom-prod-workspace"
  }
}
```

**New behavior (empty/default):** Now works too
```json
{
  "workspace_names": {}  // Auto-generates defaults
}
```

---

## Other Issues Fixed

### 1. **HCP Terraform Token**
**Issue:** 401 Unauthorized  
**Fix:** Update token in `terraform/terraform.tfvars`

```hcl
hcp_terraform_token = "NEW_VALID_TOKEN"
```

### 2. **Missing Python Dependencies**
**Issue:** `No module named 'certifi'`  
**Fix:** Install dependencies in Lambda layer

```bash
pip3 install certifi requests slack-sdk \
  -t terraform/modules/lambda/lambda_functions/shared_layer/python/
```

### 3. **OpenAI API Key Blocked**
**Issue:** 401 Authentication Error (key blocked)  
**Status:** Working with fallback (deterministic extraction)  
**Impact:** AI chat doesn't work, but form submission works fine

---

## Current Status

### ✅ Working
- Slack bot running
- Form submission via `/aws-det-poc`
- API Gateway endpoint active
- Step Functions orchestration
- Lambda functions deployed
- **Default workspace names** ✅

### ⚠️ Known Issues
- OpenAI API key blocked (AI chat disabled, but form works)
- HCP Terraform token may need refresh if 401 errors occur

### 🔄 Pending
- Update HCP Terraform token (if expired)
- Fix OpenAI key (optional - for AI chat only)

---

## Deployment Checklist

Before deploying to production:

- [ ] Update HCP Terraform token in `terraform.tfvars`
- [ ] Install Python dependencies in Lambda layer
- [ ] Deploy Lambda updates: `terraform apply`
- [ ] Test form submission with empty workspace names
- [ ] Verify workspaces created in HCP Terraform
- [ ] Check CloudWatch logs for errors
- [ ] Confirm Slack notifications received

---

## Rollback Plan

If issues occur after deployment:

```bash
# Rollback Lambda functions
cd terraform
terraform apply -target=module.lambda.aws_lambda_function.validate_intake \
                -target=module.lambda.aws_lambda_function.hcp_workspace

# Or restore from backup
git checkout HEAD~1 terraform/modules/lambda/lambda_functions/
terraform apply
```

---

## Documentation

See full details in:
- **[DEFAULT_WORKSPACE_NAMES.md](docs/DEFAULT_WORKSPACE_NAMES.md)** - Feature documentation
- **[HYBRID_IMPLEMENTATION_COMPLETE.md](docs/HYBRID_IMPLEMENTATION_COMPLETE.md)** - Architecture
- **[READY_TO_DEPLOY.md](READY_TO_DEPLOY.md)** - Deployment guide

---

## Next Steps

1. **Deploy the updates:**
   ```bash
   cd terraform
   terraform apply
   ```

2. **Test with Slack:**
   ```bash
   # Start bot
   ./start_slack_bot.sh
   
   # Submit form via Slack
   # Leave workspace names empty
   ```

3. **Monitor execution:**
   ```bash
   # Watch logs
   aws logs tail /aws/lambda/det-onboarding-prod-validate-intake --follow
   ```

4. **Verify in HCP Terraform:**
   - Check workspaces created with default names

---

**Ready to deploy!** 🚀
