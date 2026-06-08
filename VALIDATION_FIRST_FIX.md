# 🔧 Critical Fix: Validation-First Workflow

## Problem

**Two critical issues:**

1. **DynamoDB record created before validation**
   - `InitializeTracking` ran FIRST, creating a record immediately
   - If validation failed (duplicate project, missing fields, etc.), record was already in DynamoDB
   - Result: Database polluted with invalid/duplicate requests

2. **JSONPath error in NotifyFailure**
   ```
   The JSONPath '$.error' specified for the field 'error.$' could not be found
   ```
   - Step Functions expected `$.error` but validation returns `$.errors` (array)
   - Caused workflow to fail when trying to notify about validation failures

---

## Solution

### 1. Reordered Workflow Steps

**Before (BROKEN):**
```
Start → InitializeTracking → ValidateIntake → ...
        ↓ Creates record
        ↓ (even if validation fails!)
```

**After (FIXED):**
```
Start → ValidateIntake → InitializeTracking → ...
        ↓ Validate FIRST
        ↓ Only create record if valid
```

### 2. New Workflow Flow

```
┌─────────────────┐
│ ValidateIntake  │ ← START HERE (no record yet)
└────────┬────────┘
         │
    ┌────▼────┐
    │ Valid?  │
    └─┬────┬──┘
  YES │    │ NO
      │    └──────────────────┐
      │                       │
┌─────▼──────────┐   ┌────────▼──────────────┐
│ InitializeTracking │   │ NotifyValidationFailure │
│ (Create record)    │   │ (Send error to user)    │
└─────┬──────────┘   └────────┬──────────────┘
      │                       │
┌─────▼──────────┐   ┌────────▼────────┐
│ TrackValidation │   │ ValidationFailed │
│ Success         │   │ End             │
└─────┬──────────┘   └─────────────────┘
      │
┌─────▼─────────┐
│ Create Branch │
│ ...           │
```

### 3. Updated State Machine

**Key changes:**

1. **StartAt changed:**
   ```json
   "StartAt": "ValidateIntake"  // Was: "InitializeTracking"
   ```

2. **InitializeTracking moved:**
   - Now runs AFTER `CheckValidation` succeeds
   - Only creates DynamoDB record if validation passes

3. **New NotifyValidationFailure step:**
   - Handles validation failures directly
   - Sends user-friendly error message
   - Doesn't require DynamoDB record (since none was created)
   - Accepts `validation_errors` as array

4. **Removed old tracking steps:**
   - Removed `TrackValidationFailure` (no record to update)
   - Removed `ValidationFailed` tracker step

---

## Benefits

### ✅ Clean Database
- No records for invalid requests
- No records for duplicate project names
- No records for validation failures
- Only SUCCEEDED/RUNNING/FAILED workflows have records

### ✅ Better User Experience
- Validation errors shown immediately
- No "phantom" records in status lookups
- Clear error messages for duplicates

### ✅ Accurate Status
- `/aws-det-onboard-status` only shows real requests
- No confusion about which request is valid

---

## Updated Files

### 1. Step Functions State Machine
**File:** `terraform/modules/step_functions/state_machine.json.tpl`

**Changes:**
- Changed `StartAt` from `InitializeTracking` to `ValidateIntake`
- Moved `InitializeTracking` to run after validation succeeds
- Added `NotifyValidationFailure` step for failed validations
- Changed `ValidationFailedEnd` to Fail state (no tracking needed)

### 2. Completion Notifier
**File:** `terraform/modules/lambda/lambda_functions/completion_notifier/handler.py`

**Changes:**
- Added support for `validation_errors` parameter (array)
- Updated `_build_failure_message` to handle both string and array errors
- Format validation errors as bulleted list

---

## Deployment

### Option 1: Terraform (Recommended)

```bash
cd terraform
terraform apply -auto-approve
```

This will update:
- Step Functions state machine definition
- completion_notifier Lambda (if needed)

### Option 2: Manual (AWS Console)

#### Update Step Functions

1. Go to: https://console.aws.amazon.com/states/home?region=us-east-1
2. Find state machine: `det-onboarding-prod`
3. Click "Edit"
4. Replace the definition with updated `state_machine.json`
5. Click "Save"

#### Update completion_notifier Lambda

1. Go to: https://console.aws.amazon.com/lambda/home?region=us-east-1
2. Function: `det-onboarding-prod-completion-notifier`
3. Upload: `completion_notifier/completion_notifier.zip` (6.2KB)
4. Click "Save"

---

## Testing

### Test Case 1: Valid Request

```
1. Submit onboarding for "TestProj999"
2. Expected: DynamoDB record created
3. Verify: Record has service_request_id
```

### Test Case 2: Duplicate Project Name

```
1. Submit onboarding for "TestProj999" (again)
2. Expected: 
   - No DynamoDB record created
   - User gets error notification with existing SR ID
3. Verify in DynamoDB: Only ONE record for TestProj999
```

### Test Case 3: Missing Required Fields

```
1. Submit onboarding with missing field (somehow bypass Slack validation)
2. Expected:
   - No DynamoDB record created
   - User gets validation error notification
3. Verify: No record in DynamoDB for this execution
```

---

## Before vs After

### Before: Database Pollution

**User submits duplicate request:**
```
DynamoDB Records:
- SR-20260608-1234 | Status: SUCCEEDED  | Project: Dev204
- SR-20260608-7810 | Status: ??? (stuck)| Project: Dev204  ← Bad!
```

**Problem:**
- Second request created a record even though it's a duplicate
- Record exists but workflow failed at validation
- Confusing for users checking status

### After: Clean Database

**User submits duplicate request:**
```
DynamoDB Records:
- SR-20260608-1234 | Status: SUCCEEDED  | Project: Dev204
(No second record created)
```

**User receives:**
```
❌ Onboarding Failed: Dev204

Error:
• Onboarding request already exists for project 'Dev204'
  Service Request ID: SR-20260608-1234, Status: SUCCEEDED

💡 Check existing request: /aws-det-onboard-status SR-20260608-1234
```

---

## Error Handling

### Validation Errors Format

**Before:**
```json
{
  "error": "Validation failed"  // String, hard to provide details
}
```

**After:**
```json
{
  "validation_errors": [
    "Onboarding request already exists for project 'Dev204'. Service Request ID: SR-20260608-1234",
    "Missing required field: terraform_repo",
    "Invalid region: us-north-1"
  ]
}
```

**Notification shows:**
```
Error:
• Onboarding request already exists for project 'Dev204'. Service Request ID: SR-20260608-1234
• Missing required field: terraform_repo
• Invalid region: us-north-1
```

---

## Rollback Plan

If there are issues, you can rollback:

### Terraform
```bash
cd terraform
terraform plan  # Review changes
terraform apply # Revert to previous state
```

### Manual
1. Edit Step Functions state machine
2. Change `StartAt` back to `InitializeTracking`
3. Move validation checks back to original position

---

## Monitoring

### CloudWatch Logs

Check these logs after deployment:

**Step Functions:**
```
/aws/vendedlogs/states/det-onboarding-prod
```

Look for:
- Validation running BEFORE InitializeTracking
- ValidationFailedEnd executions (no records created)

**Completion Notifier:**
```
/aws/lambda/det-onboarding-prod-completion-notifier
```

Look for:
- `validation_errors` being processed
- Array error formatting

### DynamoDB

Query for project name:
```bash
aws dynamodb query \
  --table-name det-onboarding-prod-executions \
  --index-name project-name-index \
  --key-condition-expression "project_name = :pname" \
  --expression-attribute-values '{":pname":{"S":"Dev204"}}'
```

Should only show valid requests (no duplicates, no validation failures).

---

## Summary

### Changes Made

1. ✅ **Reordered workflow:** Validate FIRST, create record AFTER
2. ✅ **Fixed JSONPath error:** Handle `validation_errors` array
3. ✅ **Added NotifyValidationFailure:** Dedicated step for validation errors
4. ✅ **Updated completion_notifier:** Support array error messages

### Impact

- **Database:** No more invalid/duplicate records
- **User Experience:** Clear validation error messages
- **Status Lookup:** Only shows real requests
- **Performance:** No wasted resources on invalid requests

### Deployment Required

- **Step Functions:** State machine definition (via Terraform or Console)
- **Lambda:** completion_notifier.zip (via Console or Terraform)

**Deploy now to prevent database pollution!** 🚀
