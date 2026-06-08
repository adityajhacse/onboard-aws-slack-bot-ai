# ✨ New Feature: Duplicate Project Name Detection

## Overview

The `validate_intake` Lambda now checks if an onboarding request already exists for the same project name **before** proceeding with the workflow.

---

## How It Works

### 1. During Validation

When a user submits an onboarding request, the system:

1. **Validates** the intake data (required fields, format, etc.)
2. **Queries DynamoDB** for existing requests with the same project name
3. **Checks status** of existing requests:
   - ✅ **SUCCEEDED** → Duplicate detected, block new request
   - 🔄 **RUNNING** → Duplicate detected, block new request
   - ❌ **FAILED** → Allowed (previous attempt failed, can retry)
4. **Returns error** if duplicate found, or **proceeds** if no duplicate

### 2. Error Response

If a duplicate is found, the Lambda returns:

```json
{
  "statusCode": 400,
  "valid": false,
  "errors": [
    "Onboarding request already exists for project 'EMS'. Service Request ID: SR-20260608-1234, Status: SUCCEEDED, Created: 2026-06-08T10:30:00"
  ],
  "duplicate_request": {
    "service_request_id": "SR-20260608-1234",
    "status": "SUCCEEDED",
    "created_at": "2026-06-08T10:30:00"
  }
}
```

### 3. User Notification

The user receives a Slack notification with:

```
❌ Onboarding Failed: EMS

🎫 Service Request ID: SR-20260608-5678
👤 Requested By: @user

❌ Error:
Onboarding request already exists for project 'EMS'.
Service Request ID: SR-20260608-1234, Status: SUCCEEDED, Created: 2026-06-08T10:30:00

💡 Next Steps:
• Check the existing request: /aws-det-onboard-status SR-20260608-1234
• If you need to modify the existing setup, contact the DevOps team
• If this is a different project, use a different project name
```

---

## Implementation Details

### Code Location

**File:** `terraform/modules/lambda/lambda_functions/validate_intake/handler.py`

**Function:** `check_duplicate_project(db, project_name: str)`

```python
def check_duplicate_project(db, project_name: str) -> dict[str, Any] | None:
    """
    Check if a project with the same name already has an onboarding request.

    Returns the existing request if found, None otherwise.
    Only considers SUCCEEDED or RUNNING requests (ignores FAILED).
    """
    try:
        # Query DynamoDB by project name using GSI
        response = db.table.query(
            IndexName='project-name-index',
            KeyConditionExpression='project_name = :project_name',
            ExpressionAttributeValues={':project_name': project_name},
            ScanIndexForward=False,  # Most recent first
            Limit=10,  # Check last 10 requests for this project
        )

        items = response.get('Items', [])

        if not items:
            return None

        # Check for SUCCEEDED or RUNNING requests
        for item in items:
            status = item.get('status', '')
            if status in ('SUCCEEDED', 'RUNNING'):
                return item

        return None

    except Exception as e:
        logger.error(f"Error checking for duplicate project: {e}", exc_info=True)
        # Don't block onboarding if duplicate check fails
        return None
```

### Key Points

1. **Uses DynamoDB GSI** (`project-name-index`) for efficient queries
2. **Checks last 10 requests** for the project name (handles edge cases)
3. **Only blocks SUCCEEDED/RUNNING** requests (allows retrying FAILED requests)
4. **Fails gracefully** - if duplicate check has an error, it doesn't block the workflow
5. **Returns most recent** request info to the user

---

## Behavior Examples

### Example 1: First Request (Allowed)

**User submits:** Project name = "EMS"

**System checks:** No existing requests for "EMS"

**Result:** ✅ Request proceeds normally

---

### Example 2: Duplicate with SUCCEEDED Status (Blocked)

**User submits:** Project name = "EMS"

**System finds:** 
- Service Request: SR-20260608-1234
- Status: SUCCEEDED
- Created: 2026-06-08T10:30:00

**Result:** ❌ Request blocked with error message

**User sees:**
```
❌ Onboarding Failed: EMS
Onboarding request already exists for project 'EMS'.
Service Request ID: SR-20260608-1234, Status: SUCCEEDED
```

---

### Example 3: Previous Request FAILED (Allowed)

**User submits:** Project name = "EMS"

**System finds:**
- Service Request: SR-20260608-1234
- Status: FAILED
- Created: 2026-06-08T10:30:00

**Result:** ✅ Request proceeds (retry allowed for failed requests)

---

### Example 4: Request Currently RUNNING (Blocked)

**User submits:** Project name = "EMS"

**System finds:**
- Service Request: SR-20260608-1234
- Status: RUNNING
- Created: 2026-06-08T10:35:00 (2 minutes ago)

**Result:** ❌ Request blocked

**User sees:**
```
Onboarding request already exists for project 'EMS'.
Service Request ID: SR-20260608-1234, Status: RUNNING
```

**Next step:** User should wait for the current request to complete or check status with:
```
/aws-det-onboard-status SR-20260608-1234
```

---

## Configuration

### DynamoDB Requirements

**GSI Name:** `project-name-index`

**Hash Key:** `project_name` (String)

**Projection:** ALL

This GSI already exists in the DynamoDB table definition (`terraform/modules/dynamodb/main.tf`).

---

## Deployment

### Files Updated

1. **`validate_intake/handler.py`** - Added duplicate checking logic
2. **Package:** `validate_intake.zip` (9.7KB)

### Deploy via AWS Console

1. Go to: https://console.aws.amazon.com/lambda/home?region=us-east-1
2. Open function: `det-onboarding-prod-validate-intake`
3. Click "Upload from" → ".zip file"
4. Select: `terraform/modules/lambda/lambda_functions/validate_intake/validate_intake.zip`
5. Click "Save"

---

## Testing

### Test Case 1: Normal Flow (No Duplicate)

```
1. Submit onboarding request for project "TestProj123"
2. Expected: Request proceeds normally
3. Verify: Workflow completes successfully
```

### Test Case 2: Duplicate Detection

```
1. Submit onboarding request for project "TestProj123"
2. Wait for it to complete (status = SUCCEEDED)
3. Submit another request for project "TestProj123"
4. Expected: Request is blocked with error message
5. Verify: 
   - User receives failure notification
   - Error message mentions existing Service Request ID
   - Workflow stops at validation step
```

### Test Case 3: Retry After Failure

```
1. Submit onboarding request for project "TestProj456" (intentionally fail it somehow)
2. Verify status is FAILED
3. Submit another request for project "TestProj456"
4. Expected: Request is allowed (retrying failed request)
5. Verify: Workflow proceeds normally
```

---

## User Experience

### Before (Without Duplicate Check)

**Problem:**
- Users could create multiple onboarding requests for the same project
- Resulted in duplicate infrastructure resources
- Caused confusion about which request was correct
- Wasted resources and time

### After (With Duplicate Check)

**Solution:**
- System prevents duplicate requests immediately
- Users get clear feedback about existing request
- Includes Service Request ID of existing request for reference
- Users can check status of existing request with `/aws-det-onboard-status`

---

## Edge Cases Handled

### 1. Duplicate Check Failure

If the duplicate check query fails (e.g., DynamoDB timeout):
- **Behavior:** Request proceeds anyway (fail-open)
- **Reason:** Don't block legitimate requests due to infrastructure issues
- **Logged:** Error is logged in CloudWatch for monitoring

### 2. Multiple Requests Simultaneously

If two users submit requests for the same project at exactly the same time:
- **First request:** Passes duplicate check (no duplicates yet)
- **Second request:** May also pass (race condition)
- **Mitigation:** This is an acceptable edge case. The GSI will eventually show both, and the second can be manually cancelled if needed.

### 3. Case Sensitivity

Project names are **case-sensitive**:
- "EMS" ≠ "ems" ≠ "Ems"
- Each is treated as a different project

### 4. Partial Name Matches

Only **exact matches** are blocked:
- "EMS" does not conflict with "EMS-API"
- "Test" does not conflict with "Test-Project"

---

## Monitoring

### CloudWatch Logs

Check `/aws/lambda/det-onboarding-prod-validate-intake` for:

**Successful duplicate detection:**
```
Found duplicate request for project 'EMS': SR ID=SR-20260608-1234, Status=SUCCEEDED
```

**No duplicates found:**
```
No existing requests found for project: EMS
```

**Duplicate check error:**
```
Error checking for duplicate project: [error details]
```

---

## Future Enhancements

Potential improvements:

1. **Configurable Behavior**
   - Environment variable to enable/disable duplicate checking
   - Environment variable to control which statuses block duplicates

2. **Grace Period**
   - Allow duplicates if previous request is older than X days
   - Useful for projects that get decommissioned and re-onboarded

3. **Force Flag**
   - Special flag to bypass duplicate check (admin only)
   - For legitimate re-onboarding scenarios

4. **Fuzzy Matching**
   - Detect similar project names ("EMS" vs "ems")
   - Warn user about potential confusion

5. **Workspace-Specific Duplicates**
   - Allow same project name in different AWS accounts/workspaces
   - Add workspace context to duplicate check

---

## Summary

✅ **Feature:** Duplicate project name detection in `validate_intake`

✅ **Blocks:** Requests for projects with SUCCEEDED or RUNNING status

✅ **Allows:** Retrying failed requests

✅ **User Feedback:** Clear error message with existing Service Request ID

✅ **Deployment:** Single Lambda function update (`validate_intake.zip`)

✅ **Fail-Safe:** Errors in duplicate check don't block legitimate requests

**Deploy now to prevent duplicate onboarding requests!** 🚀
