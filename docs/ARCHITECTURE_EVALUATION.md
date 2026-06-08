# Architecture Evaluation & Enhancement Plan

**Date:** 2026-06-08  
**Purpose:** Evaluate current architecture and provide implementation plan for enhanced status tracking and user notifications

---

## Executive Summary

The current AWS DET Onboarding Bot architecture is **80% aligned** with the new requirements. The foundation for real-time status tracking, DynamoDB record creation, and Step Functions orchestration is already in place.

**Key Findings:**
- ✅ DynamoDB record creation already happens at API Gateway invocation
- ✅ Step-level status tracking infrastructure exists
- ✅ Real-time DynamoDB updates are implemented
- ⚠️ Missing: Immediate Slack notification after ValidateIntake
- ⚠️ Missing: Dedicated status columns need enhancement
- ❌ Missing: `/aws-det-onboard-status` slash command
- ❌ Missing: User-facing Service Request ID in notifications

**Estimated Implementation Effort:** 8-12 hours

---

## Current Architecture Analysis

### ✅ What's Already Working

#### 1. DynamoDB Record Creation on API Gateway Invocation

**Current Implementation:**
- Location: Step Functions → `InitializeTracking` state
- Lambda: `status_tracker` with action "start"
- File: `terraform/modules/lambda/lambda_functions/status_tracker/handler.py`

```json
"InitializeTracking": {
  "Type": "Task",
  "Resource": "${status_tracker_arn}",
  "Parameters": {
    "action": "start",
    "execution_id.$": "$$.Execution.Name",
    "intake.$": "$.intake",
    "slack_channel.$": "$.slack_channel",
    "slack_user.$": "$.slack_user"
  },
  "Next": "ValidateIntake"
}
```

**Status:** ✅ **COMPLETE** - Records are created immediately when Step Functions starts

---

#### 2. Step-Level Status Columns in DynamoDB

**Current Implementation:**
- Table: `det-onboarding-prod-executions`
- Module: `dynamodb_helper.py` → `create_execution_record()`

Current schema includes a `steps` object with all pipeline steps:

```python
'steps': {
    'ValidateIntake': {'status': 'PENDING'},
    'CreateGitHubBranch': {'status': 'PENDING'},
    'CommitToGitHub': {'status': 'PENDING'},
    'CreateHCPProject': {'status': 'PENDING'},
    'CreateWorkspaces': {'status': 'PENDING'},
    'ConfigureVariables': {'status': 'PENDING'},
}
```

Each step tracks:
- `status`: PENDING | RUNNING | SUCCEEDED | FAILED | SKIPPED
- `started_at`: ISO timestamp
- `completed_at`: ISO timestamp
- `result`: Step output data
- `error`: Error message if failed

**Status:** ✅ **COMPLETE** - All six pipeline steps have dedicated status tracking

---

#### 3. Real-Time DynamoDB Status Updates

**Current Implementation:**
- Module: `dynamodb_helper.py` → `update_step_status()`
- Called by: Each Lambda function after processing

Example from `github_branch/handler.py`:

```python
db_helper = get_helper()
db_helper.update_step_status(
    execution_id=execution_id,
    step_name='CreateGitHubBranch',
    status='SUCCEEDED',
    result={'branch_name': branch_name}
)
```

**Status:** ✅ **COMPLETE** - Real-time updates after each step completes

---

#### 4. Request Tracking by Execution ID

**Current Implementation:**
- Primary Key: `execution_id` (String)
- Format: Step Functions execution name (UUID-based)
- GSI: `slack-channel-index`, `project-name-index`, `status-index`

Functions available:
- `get_execution(execution_id)` → Retrieve by ID
- `get_executions_by_channel(slack_channel)` → Recent requests
- `get_execution_logs(execution_id)` → Detailed logs

**Status:** ✅ **COMPLETE** - Full tracking infrastructure exists

---

### ⚠️ What Needs Enhancement

#### 1. User-Friendly Service Request ID

**Current State:**
- Execution ID format: AWS-generated UUID
- Example: `arn:aws:states:us-east-1:123456789012:execution:det-onboarding-prod:abc123-def456-ghi789`

**Problem:**
- Too long and technical for end users
- Not user-friendly for Slack conversations
- Difficult to remember and type

**Required Enhancement:**
Create a **human-readable Service Request ID** that maps to the execution ID:
- Format: `SR-{YYYYMMDD}-{4-digit-counter}`
- Example: `SR-20260608-0042`
- Shorter alternative: `SR-{6-char-alphanumeric}`
- Example: `SR-K7X9M2`

**Implementation Required:**
- Add `service_request_id` field to DynamoDB schema
- Generate in `InitializeTracking` state
- Return in all user-facing messages
- Create GSI for quick lookup: `service-request-id-index`

---

#### 2. DynamoDB Schema Enhancement

**Current Schema:**
```python
{
  "execution_id": "abc123-def456",
  "status": "RUNNING",
  "steps": {
    "ValidateIntake": {
      "status": "SUCCEEDED",
      "started_at": "...",
      "completed_at": "..."
    }
  }
}
```

**Enhanced Schema Required:**
```python
{
  "execution_id": "abc123-def456",
  "service_request_id": "SR-20260608-0042",  # NEW
  "status": "RUNNING",
  
  # Enhanced step tracking (flattened for easier queries)
  "step_validate_intake": "SUCCEEDED",        # NEW
  "step_github_branch": "SUCCEEDED",          # NEW
  "step_github_commit": "RUNNING",            # NEW
  "step_hcp_project": "PENDING",              # NEW
  "step_workspaces": "PENDING",               # NEW
  "step_variables": "PENDING",                # NEW
  
  # Keep existing nested structure for detailed data
  "steps": {
    "ValidateIntake": {
      "status": "SUCCEEDED",
      "started_at": "2026-06-08T10:00:00Z",
      "completed_at": "2026-06-08T10:00:03Z",
      "result": {...}
    }
  }
}
```

**Benefits:**
- Flattened columns enable simple status queries
- Easier to create status dashboards
- Compatible with existing nested structure
- No breaking changes to current code

---

### ❌ What's Missing Entirely

#### 1. Immediate Slack Notification After ValidateIntake

**Current Behavior:**
- User submits form → API Gateway called
- No immediate feedback
- User waits ~30-45 seconds
- Final notification sent via `completion_notifier`

**Required Behavior:**
- ValidateIntake completes → **Immediate Slack message**
- Message includes:
  - ✅ Validation passed
  - 🎫 Service Request ID: `SR-20260608-0042`
  - 📊 Status tracking instructions
  - ⏱️ Expected completion time

**Implementation Required:**
- Create new Lambda: `validation_notifier`
- Insert in Step Functions after `TrackValidationSuccess`
- Send Slack message with Service Request ID

**Workflow Change:**
```
ValidateIntake
    ↓
TrackValidationSuccess
    ↓
SendValidationNotification  ← NEW STEP
    ↓
CheckValidation
    ↓
CreateGitHubBranch
```

---

#### 2. Slash Command: `/aws-det-onboard-status`

**Current State:**
- ❌ Does not exist
- Users have no way to check status
- No self-service status lookup

**Required Implementation:**

**Command:** `/aws-det-onboard-status`

**User Flow:**
1. User types: `/aws-det-onboard-status`
2. Bot responds: "Please enter your Service Request ID:"
3. User replies: `SR-20260608-0042`
4. Bot queries DynamoDB by `service_request_id`
5. Bot responds with formatted status summary

**Response Format:**
```
📋 Service Request Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎫 Request ID: SR-20260608-0042
📦 Project: CustomerAPI
⏱️  Started: 2 minutes ago
🔄 Status: IN PROGRESS

Pipeline Steps:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Validate Intake         PASSED
✅ Create GitHub Branch     PASSED
✅ Commit to GitHub         PASSED
🔄 Create HCP Project       RUNNING
⏳ Create Workspaces        PENDING
⏳ Configure Variables      PENDING

━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Your request is being processed. You'll receive a notification when complete.
```

**Implementation Components:**
1. **Slack Command Handler** (`src/main_with_api_gateway.py`)
2. **Status Query Lambda** (optional, or query directly from bot)
3. **Response Formatter** (pretty-print status)

---

#### 3. Enhanced Completion Notification

**Current Completion Message:**
- Generic success/failure message
- Includes resource links
- Sent by `completion_notifier` Lambda

**Enhanced Message Should Include:**
- 🎫 Service Request ID prominently
- Reference to track future requests
- Summary of what was created

**Example Enhancement:**
```
✅ Onboarding Complete!

🎫 Service Request ID: SR-20260608-0042

Your infrastructure for CustomerAPI is ready:
✅ GitHub Branch: customer-api-onboard
✅ HCP Project: CustomerAPI
✅ Workspaces Created: Dev, Prod
✅ Variables Configured: 12 variables

Track this request anytime with:
/aws-det-onboard-status

━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ Completed in 42 seconds
```

---

## Gap Analysis Summary

| Requirement | Current Status | Gap | Effort |
|-------------|---------------|-----|---------|
| **1. DynamoDB record on API Gateway invocation** | ✅ Implemented | None | 0h |
| **2. Step-level status columns** | ✅ Implemented | Enhance with flattened columns | 2h |
| **3. Slack notification after ValidateIntake** | ❌ Missing | New Lambda + Step Functions state | 3h |
| **4. Real-time DynamoDB updates** | ✅ Implemented | None | 0h |
| **5. Request tracking by Service Request ID** | ⚠️ Partial | Generate user-friendly ID | 2h |
| **6. `/aws-det-onboard-status` command** | ❌ Missing | New slash command + handler | 4h |
| **7. Detailed status summary** | ⚠️ Partial | Format and display logic | 2h |

**Total Implementation Effort:** ~13 hours (rounded to 8-12 hours with reuse)

---

## Implementation Plan

### Phase 1: DynamoDB Schema Enhancement (2-3 hours)

**Goal:** Add Service Request ID and flattened status columns

#### Step 1.1: Update DynamoDB Schema

**File:** `terraform/modules/dynamodb/main.tf`

Add new attributes and GSI:

```hcl
attribute {
  name = "service_request_id"
  type = "S"
}

global_secondary_index {
  name            = "service-request-id-index"
  hash_key        = "service_request_id"
  projection_type = "ALL"
}
```

#### Step 1.2: Update DynamoDB Helper

**File:** `terraform/modules/lambda/lambda_functions/shared_layer/python/dynamodb_helper.py`

**Changes:**

1. **Add ID generator:**
```python
import random
import string
from datetime import datetime

def generate_service_request_id() -> str:
    """
    Generate human-friendly Service Request ID.
    Format: SR-YYYYMMDD-XXXX (where XXXX is 4-digit counter)
    Alternative: SR-{6-char-alphanumeric}
    """
    # Option 1: Date-based with counter
    date_str = datetime.utcnow().strftime('%Y%m%d')
    counter = random.randint(1000, 9999)
    return f"SR-{date_str}-{counter}"
    
    # Option 2: Short alphanumeric (simpler, more compact)
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(chars, k=6))
    return f"SR-{code}"
```

2. **Update `create_execution_record()`:**
```python
def create_execution_record(
    self,
    execution_id: str,
    intake: dict[str, Any],
    slack_channel: str,
    slack_user: str,
) -> dict[str, Any]:
    now = datetime.utcnow()
    ttl = int((now + timedelta(days=90)).timestamp())
    
    # Generate Service Request ID
    service_request_id = self.generate_service_request_id()

    record = {
        'execution_id': execution_id,
        'service_request_id': service_request_id,  # NEW
        'status': 'RUNNING',
        'current_step': 'ValidateIntake',
        
        # Flattened step status columns (NEW)
        'step_validate_intake': 'PENDING',
        'step_github_branch': 'PENDING',
        'step_github_commit': 'PENDING',
        'step_hcp_project': 'PENDING',
        'step_workspaces': 'PENDING',
        'step_variables': 'PENDING',
        
        # Existing nested structure
        'steps': {
            'ValidateIntake': {'status': 'PENDING'},
            'CreateGitHubBranch': {'status': 'PENDING'},
            'CommitToGitHub': {'status': 'PENDING'},
            'CreateHCPProject': {'status': 'PENDING'},
            'CreateWorkspaces': {'status': 'PENDING'},
            'ConfigureVariables': {'status': 'PENDING'},
        },
        # ... rest of record
    }
    
    return record
```

3. **Update `update_step_status()`:**
```python
def update_step_status(
    self,
    execution_id: str,
    step_name: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    # Map step names to flattened column names
    step_column_map = {
        'ValidateIntake': 'step_validate_intake',
        'CreateGitHubBranch': 'step_github_branch',
        'CommitToGitHub': 'step_github_commit',
        'CreateHCPProject': 'step_hcp_project',
        'CreateWorkspaces': 'step_workspaces',
        'ConfigureVariables': 'step_variables',
    }
    
    # Update both nested and flattened status
    update_expression = [
        'current_step = :step',
        'updated_at = :updated',
        f'steps.{step_name}.#status = :step_status',
        f'{step_column_map[step_name]} = :step_status',  # NEW
    ]
    # ... rest of method
```

4. **Add lookup by Service Request ID:**
```python
def get_execution_by_service_request_id(
    self,
    service_request_id: str,
) -> dict[str, Any] | None:
    """
    Get execution record by Service Request ID.
    
    Args:
        service_request_id: User-friendly ID (e.g., SR-20260608-0042)
    
    Returns:
        Execution record or None if not found
    """
    try:
        response = self.table.query(
            IndexName='service-request-id-index',
            KeyConditionExpression='service_request_id = :sr_id',
            ExpressionAttributeValues={':sr_id': service_request_id},
            Limit=1,
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except ClientError as e:
        logger.error(f"Failed to get execution by SR ID: {e}")
        return None
```

#### Step 1.3: Deploy Schema Changes

```bash
cd terraform
terraform plan
terraform apply
```

**Validation:**
- Table has new `service_request_id` attribute
- GSI `service-request-id-index` exists
- No data loss from existing records

---

### Phase 2: Immediate Slack Notification (3-4 hours)

**Goal:** Send notification immediately after ValidateIntake passes

#### Step 2.1: Create Validation Notifier Lambda

**File:** `terraform/modules/lambda/lambda_functions/validation_notifier/handler.py`

```python
import json
import logging
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Send immediate Slack notification after successful validation.
    
    Input event:
    {
        "execution_id": "abc123-def456",
        "service_request_id": "SR-20260608-0042",
        "slack_channel": "C123456",
        "slack_user": "U789012",
        "project_name": "CustomerAPI",
        "intake": {...}
    }
    """
    try:
        execution_id = event.get('execution_id')
        service_request_id = event.get('service_request_id')
        slack_channel = event.get('slack_channel')
        slack_user = event.get('slack_user')
        project_name = event.get('project_name')
        
        # Initialize Slack client
        slack_token = os.environ['SLACK_BOT_TOKEN']
        client = WebClient(token=slack_token)
        
        # Build message
        message = build_validation_success_message(
            service_request_id=service_request_id,
            project_name=project_name,
            user_id=slack_user,
        )
        
        # Send to Slack
        response = client.chat_postMessage(
            channel=slack_channel,
            blocks=message['blocks'],
            text=message['text'],
        )
        
        logger.info(f"Validation notification sent for {service_request_id}")
        
        return {
            'statusCode': 200,
            'notification_sent': True,
            'message_ts': response['ts']
        }
        
    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        # Don't fail the workflow if notification fails
        return {'statusCode': 500, 'notification_sent': False}
    except Exception as e:
        logger.error(f"Notification error: {str(e)}", exc_info=True)
        return {'statusCode': 500, 'notification_sent': False}


def build_validation_success_message(service_request_id, project_name, user_id):
    """Build Slack message blocks for validation success."""
    return {
        'text': f'✅ Onboarding request validated for {project_name}',
        'blocks': [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': '✅ Your Onboarding Request is Being Processed',
                    'emoji': True
                }
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"<@{user_id}> Your infrastructure onboarding for *{project_name}* has been validated and is now in progress."
                }
            },
            {
                'type': 'section',
                'fields': [
                    {
                        'type': 'mrkdwn',
                        'text': f'*🎫 Service Request ID:*\n`{service_request_id}`'
                    },
                    {
                        'type': 'mrkdwn',
                        'text': '*⏱️ Estimated Time:*\n~30-45 seconds'
                    }
                ]
            },
            {
                'type': 'divider'
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': (
                        '💡 *Track Your Request:*\n'
                        f'Use `/aws-det-onboard-status` with ID `{service_request_id}` '
                        'to check progress anytime.'
                    )
                }
            },
            {
                'type': 'context',
                'elements': [
                    {
                        'type': 'mrkdwn',
                        'text': "You'll receive another notification when your infrastructure is ready."
                    }
                ]
            }
        ]
    }
```

#### Step 2.2: Add Lambda to Terraform

**File:** `terraform/modules/lambda/main.tf`

Add new Lambda function:

```hcl
# Validation Notifier Lambda
resource "aws_lambda_function" "validation_notifier" {
  function_name = "${var.name_prefix}-validation-notifier"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  role          = var.lambda_role_arn
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.validation_notifier.output_path
  source_code_hash = data.archive_file.validation_notifier.output_base64sha256

  layers = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = {
      SLACK_BOT_TOKEN = var.slack_bot_token
    }
  }

  tags = var.tags
}

data "archive_file" "validation_notifier" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_functions/validation_notifier"
  output_path = "${path.module}/.terraform/validation_notifier.zip"
}
```

#### Step 2.3: Update Step Functions State Machine

**File:** `terraform/modules/step_functions/state_machine.json.tpl`

Insert new state after `TrackValidationSuccess`:

```json
"TrackValidationSuccess": {
  "Type": "Task",
  "Resource": "${status_tracker_arn}",
  "Parameters": {
    "action": "step_update",
    "execution_id.$": "$$.Execution.Name",
    "step_name": "ValidateIntake",
    "step_status": "SUCCEEDED",
    "result.$": "$.intake"
  },
  "ResultPath": "$.tracking_result",
  "Next": "SendValidationNotification",
  "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "SendValidationNotification"}]
},
"SendValidationNotification": {
  "Type": "Task",
  "Resource": "${validation_notifier_arn}",
  "Comment": "Notify user that validation passed",
  "Parameters": {
    "execution_id.$": "$$.Execution.Name",
    "service_request_id.$": "$.tracking_result.service_request_id",
    "slack_channel.$": "$.slack_channel",
    "slack_user.$": "$.slack_user",
    "project_name.$": "$.intake.project_name",
    "intake.$": "$.intake"
  },
  "ResultPath": "$.validation_notification",
  "Next": "CheckValidation",
  "Catch": [{
    "ErrorEquals": ["States.ALL"],
    "ResultPath": "$.notification_error",
    "Next": "CheckValidation"
  }]
},
"CheckValidation": {
  "Type": "Choice",
  "Choices": [{
    "Variable": "$.valid",
    "BooleanEquals": true,
    "Next": "CreateGitHubBranch"
  }],
  "Default": "ValidationFailed"
}
```

**Key Points:**
- Non-blocking: Notification failure doesn't stop workflow
- Service Request ID passed from tracking result
- Immediate feedback to user

---

### Phase 3: Status Lookup Command (4-5 hours)

**Goal:** Implement `/aws-det-onboard-status` slash command

#### Step 3.1: Add Slash Command Handler

**File:** `src/main_with_api_gateway.py`

Add new command handler:

```python
@app.command("/aws-det-onboard-status")
def aws_det_status(ack, body, client, respond):
    """Handle status lookup command."""
    ack()
    
    channel_id = body.get("channel_id", "")
    user_id = body.get("user_id", "")
    text = body.get("text", "").strip()
    
    # If SR ID provided in command text
    if text and text.upper().startswith("SR-"):
        service_request_id = text.upper()
        show_status(client, channel_id, user_id, service_request_id)
    else:
        # Prompt for SR ID
        prompt_for_service_request_id(client, channel_id, user_id)


def prompt_for_service_request_id(client, channel_id, user_id):
    """Ask user for their Service Request ID."""
    try:
        client.chat_postMessage(
            channel=channel_id,
            text=f"<@{user_id}> Please provide your Service Request ID (e.g., `SR-20260608-0042`).",
            blocks=[
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': (
                            f"<@{user_id}> To check your onboarding status, please reply with "
                            "your *Service Request ID*.\n\n"
                            "Example: `SR-20260608-0042`\n\n"
                            "_You received this ID when you submitted your onboarding request._"
                        )
                    }
                }
            ]
        )
    except SlackApiError as e:
        logging.error(f"Failed to prompt for SR ID: {e}")


def show_status(client, channel_id, user_id, service_request_id):
    """Query DynamoDB and display status."""
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        # Query DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('DYNAMODB_TABLE', 'det-onboarding-prod-executions')
        table = dynamodb.Table(table_name)
        
        response = table.query(
            IndexName='service-request-id-index',
            KeyConditionExpression='service_request_id = :sr_id',
            ExpressionAttributeValues={':sr_id': service_request_id},
            Limit=1
        )
        
        items = response.get('Items', [])
        
        if not items:
            # SR ID not found
            client.chat_postMessage(
                channel=channel_id,
                text=f"❌ Service Request ID `{service_request_id}` not found.",
                blocks=[
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': (
                                f"❌ <@{user_id}> I couldn't find a request with ID `{service_request_id}`.\n\n"
                                "*Please check:*\n"
                                "• ID is correct (case-sensitive)\n"
                                "• Request was submitted less than 90 days ago\n"
                                "• You're in the correct Slack workspace"
                            )
                        }
                    }
                ]
            )
            return
        
        # Found - format and display
        execution = items[0]
        message = format_status_message(execution, user_id)
        
        client.chat_postMessage(
            channel=channel_id,
            blocks=message['blocks'],
            text=message['text']
        )
        
    except ClientError as e:
        logging.error(f"DynamoDB error: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"❌ <@{user_id}> Error retrieving status. Please try again later."
        )
    except Exception as e:
        logging.error(f"Status lookup error: {e}", exc_info=True)
        client.chat_postMessage(
            channel=channel_id,
            text=f"❌ <@{user_id}> An error occurred. Please contact support."
        )


def format_status_message(execution, user_id):
    """Format execution status as Slack message blocks."""
    from datetime import datetime, timezone
    
    service_request_id = execution.get('service_request_id', 'N/A')
    project_name = execution.get('project_name', 'Unknown')
    status = execution.get('status', 'UNKNOWN')
    created_at = execution.get('created_at', '')
    completed_at = execution.get('completed_at')
    
    # Calculate time elapsed
    if created_at:
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if completed_at:
            completed = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            elapsed = completed - created
            time_display = f"Completed in {elapsed.seconds} seconds"
        else:
            now = datetime.now(timezone.utc)
            elapsed = now - created
            minutes = elapsed.seconds // 60
            seconds = elapsed.seconds % 60
            time_display = f"Running for {minutes}m {seconds}s"
    else:
        time_display = "Unknown"
    
    # Status emoji
    status_emoji = {
        'RUNNING': '🔄',
        'SUCCEEDED': '✅',
        'FAILED': '❌'
    }.get(status, '❓')
    
    # Step statuses
    step_validate = execution.get('step_validate_intake', 'UNKNOWN')
    step_branch = execution.get('step_github_branch', 'UNKNOWN')
    step_commit = execution.get('step_github_commit', 'UNKNOWN')
    step_project = execution.get('step_hcp_project', 'UNKNOWN')
    step_workspaces = execution.get('step_workspaces', 'UNKNOWN')
    step_variables = execution.get('step_variables', 'UNKNOWN')
    
    def step_emoji(status):
        return {
            'SUCCEEDED': '✅',
            'RUNNING': '🔄',
            'FAILED': '❌',
            'PENDING': '⏳',
            'SKIPPED': '⏭️'
        }.get(status, '❓')
    
    # Build message
    blocks = [
        {
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': f'{status_emoji} Service Request Status',
                'emoji': True
            }
        },
        {
            'type': 'section',
            'fields': [
                {
                    'type': 'mrkdwn',
                    'text': f'*🎫 Request ID:*\n`{service_request_id}`'
                },
                {
                    'type': 'mrkdwn',
                    'text': f'*📦 Project:*\n{project_name}'
                },
                {
                    'type': 'mrkdwn',
                    'text': f'*🔄 Status:*\n{status}'
                },
                {
                    'type': 'mrkdwn',
                    'text': f'*⏱️ Time:*\n{time_display}'
                }
            ]
        },
        {
            'type': 'divider'
        },
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': '*Pipeline Steps:*'
            }
        },
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': (
                    f"{step_emoji(step_validate)} *Validate Intake* - {step_validate}\n"
                    f"{step_emoji(step_branch)} *Create GitHub Branch* - {step_branch}\n"
                    f"{step_emoji(step_commit)} *Commit to GitHub* - {step_commit}\n"
                    f"{step_emoji(step_project)} *Create HCP Project* - {step_project}\n"
                    f"{step_emoji(step_workspaces)} *Create Workspaces* - {step_workspaces}\n"
                    f"{step_emoji(step_variables)} *Configure Variables* - {step_variables}"
                )
            }
        },
        {
            'type': 'divider'
        }
    ]
    
    # Add status-specific footer
    if status == 'RUNNING':
        blocks.append({
            'type': 'context',
            'elements': [{
                'type': 'mrkdwn',
                'text': f"💡 <@{user_id}> Your request is being processed. Check back in a moment or wait for completion notification."
            }]
        })
    elif status == 'SUCCEEDED':
        blocks.append({
            'type': 'context',
            'elements': [{
                'type': 'mrkdwn',
                'text': f"✅ <@{user_id}> Your infrastructure is ready! Check your notifications for resource links."
            }]
        })
    elif status == 'FAILED':
        error_msg = execution.get('error_message', 'Unknown error')
        blocks.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"*❌ Error:*\n```{error_msg}```"
            }
        })
        blocks.append({
            'type': 'context',
            'elements': [{
                'type': 'mrkdwn',
                'text': f"<@{user_id}> Please contact support for assistance."
            }]
        })
    
    return {
        'text': f'{status_emoji} Status for {service_request_id}: {status}',
        'blocks': blocks
    }
```

#### Step 3.2: Handle Message Responses

Add message event handler to capture SR ID when user replies:

```python
@app.event("message")
def handle_message_events(event, client, say):
    """Handle direct messages and thread responses."""
    text = event.get("text", "").strip()
    user = event.get("user")
    channel = event.get("channel")
    
    # Check if message looks like Service Request ID
    if text.upper().startswith("SR-") and len(text) >= 9:
        service_request_id = text.upper()
        show_status(client, channel, user, service_request_id)
```

#### Step 3.3: Update Bot Permissions

Ensure bot has permission to:
- Read messages in channels
- Post messages
- Use commands

**File:** Slack App Manifest (configured in Slack App settings)

Required OAuth Scopes:
- `commands` - Slash commands
- `chat:write` - Post messages
- `channels:history` - Read messages (if needed)

---

### Phase 4: Enhanced Completion Notification (1-2 hours)

**Goal:** Include Service Request ID in final notification

#### Step 4.1: Update Completion Notifier Lambda

**File:** `terraform/modules/lambda/lambda_functions/completion_notifier/handler.py`

**Changes:**

1. **Retrieve Service Request ID from DynamoDB:**

```python
def lambda_handler(event, context):
    execution_id = event.get('execution_id')
    
    # Get full execution record to retrieve Service Request ID
    from dynamodb_helper import get_helper
    db_helper = get_helper()
    execution = db_helper.get_execution(execution_id)
    
    service_request_id = execution.get('service_request_id', 'N/A')
    
    # Build message with SR ID
    message = build_completion_message(
        service_request_id=service_request_id,
        project_name=event.get('project_name'),
        status=event.get('status'),
        result=event.get('result'),
    )
    
    # Send to Slack
    # ...
```

2. **Update message template:**

```python
def build_completion_message(service_request_id, project_name, status, result):
    """Build enhanced completion message."""
    
    if status == 'SUCCEEDED':
        return {
            'blocks': [
                {
                    'type': 'header',
                    'text': {
                        'type': 'plain_text',
                        'text': '✅ Onboarding Complete!',
                        'emoji': True
                    }
                },
                {
                    'type': 'section',
                    'fields': [
                        {
                            'type': 'mrkdwn',
                            'text': f'*🎫 Service Request ID:*\n`{service_request_id}`'
                        },
                        {
                            'type': 'mrkdwn',
                            'text': f'*📦 Project:*\n{project_name}'
                        }
                    ]
                },
                # ... existing success details ...
                {
                    'type': 'divider'
                },
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': (
                            '💡 *Track Future Requests:*\n'
                            f'Save your Service Request ID `{service_request_id}` for reference. '
                            'Use `/aws-det-onboard-status` anytime to check status.'
                        )
                    }
                }
            ]
        }
```

---

## Testing Plan

### Unit Tests

**Test 1: Service Request ID Generation**
```python
def test_service_request_id_format():
    sr_id = generate_service_request_id()
    assert sr_id.startswith('SR-')
    assert len(sr_id) >= 9
    assert sr_id[3:].replace('-', '').isalnum()
```

**Test 2: DynamoDB Schema**
```python
def test_execution_record_has_service_request_id():
    record = db_helper.create_execution_record(...)
    assert 'service_request_id' in record
    assert record['service_request_id'].startswith('SR-')
```

**Test 3: Status Lookup**
```python
def test_get_execution_by_service_request_id():
    sr_id = 'SR-20260608-0042'
    execution = db_helper.get_execution_by_service_request_id(sr_id)
    assert execution is not None
    assert execution['service_request_id'] == sr_id
```

### Integration Tests

**Test 4: End-to-End Workflow**
1. Submit onboarding request via Slack
2. Verify immediate notification contains SR ID
3. Use `/aws-det-onboard-status` with SR ID
4. Verify status displayed correctly
5. Wait for completion
6. Verify final notification contains SR ID

**Test 5: Status Command Edge Cases**
- Invalid SR ID format
- Non-existent SR ID
- Expired SR ID (> 90 days)
- Concurrent status checks

### Load Tests

**Test 6: Concurrent Onboardings**
- Create 10 simultaneous requests
- Verify unique SR IDs generated
- Verify no collisions in DynamoDB

---

## Deployment Checklist

### Pre-Deployment

- [ ] Review all code changes
- [ ] Run unit tests locally
- [ ] Test DynamoDB schema changes in dev environment
- [ ] Backup existing DynamoDB table
- [ ] Review IAM permissions for new Lambda
- [ ] Update documentation

### Deployment Steps

1. **Deploy Infrastructure (Terraform)**
   ```bash
   cd terraform
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

2. **Deploy Slack Bot**
   ```bash
   # Restart bot to load new command handlers
   python src/main_with_api_gateway.py
   ```

3. **Verify Deployment**
   ```bash
   # Check Lambda functions exist
   aws lambda list-functions --query 'Functions[?contains(FunctionName, `validation-notifier`)]'
   
   # Check DynamoDB GSI
   aws dynamodb describe-table --table-name det-onboarding-prod-executions \
     --query 'Table.GlobalSecondaryIndexes[?IndexName==`service-request-id-index`]'
   ```

### Post-Deployment

- [ ] Test end-to-end workflow in production
- [ ] Monitor CloudWatch logs for errors
- [ ] Test `/aws-det-onboard-status` command
- [ ] Verify notifications sent correctly
- [ ] Monitor DynamoDB query performance

---

## Rollback Plan

If issues occur after deployment:

1. **Revert Terraform Changes:**
   ```bash
   cd terraform
   terraform apply -auto-approve -var-file=previous_version.tfvars
   ```

2. **Restore DynamoDB Schema:**
   - Remove `service-request-id-index` GSI
   - DynamoDB gracefully handles missing attributes (no data loss)

3. **Revert Slack Bot:**
   ```bash
   git checkout <previous-commit>
   python src/main_with_api_gateway.py
   ```

---

## Timeline Estimate

| Phase | Tasks | Estimated Hours |
|-------|-------|----------------|
| **Phase 1** | DynamoDB schema + helper updates | 2-3h |
| **Phase 2** | Validation notifier Lambda + Step Functions | 3-4h |
| **Phase 3** | Status command implementation | 4-5h |
| **Phase 4** | Enhanced completion notification | 1-2h |
| **Testing** | Unit + integration tests | 2-3h |
| **Deployment** | Deploy + verify | 1h |
| **Total** | | **13-18h** |

**Recommended Schedule:**
- Day 1: Phase 1 + Phase 2
- Day 2: Phase 3
- Day 3: Phase 4 + Testing + Deployment

---

## Success Metrics

Track these metrics post-deployment:

1. **User Adoption**
   - Number of `/aws-det-onboard-status` uses per day
   - Percentage of users checking status before completion

2. **System Performance**
   - Average time from submission to validation notification
   - DynamoDB query latency for SR ID lookups

3. **User Satisfaction**
   - Reduction in "Where's my request?" questions
   - Feedback on SR ID usability

---

## Conclusion

The current architecture is **well-positioned** to support the new requirements with minimal changes. The foundation is solid:

✅ DynamoDB tracking exists  
✅ Real-time updates implemented  
✅ Step Functions orchestration working  

**Key Additions Required:**
1. User-friendly Service Request ID generation
2. Immediate Slack notification after validation
3. `/aws-det-onboard-status` slash command
4. Enhanced status formatting

**Total Effort:** 13-18 hours over 3 days

**Risk Level:** Low - Changes are additive, non-breaking

**Recommendation:** Proceed with phased implementation, starting with Phase 1 (DynamoDB schema) to establish the foundation for subsequent phases.

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-08  
**Author:** Architecture Evaluation Team
