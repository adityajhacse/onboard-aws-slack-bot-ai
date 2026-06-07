# DynamoDB Status Tracking - Quick Guide

## What Was Added

Enhanced the Step Functions architecture with **complete job tracking and status monitoring** using DynamoDB tables.

## New Components

### 1. **Two DynamoDB Tables**

#### Executions Table (`det-onboarding-prod-executions`)
- **Stores**: Complete service records and job status
- **Contains**: Project details, intake data, step status, results, errors
- **Indexes**: Query by channel, project, or status
- **TTL**: Auto-delete after 90 days

#### Execution Logs Table (`det-onboarding-prod-execution-logs`)
- **Stores**: Detailed step-by-step logs with timestamps
- **Contains**: Each state transition with millisecond precision
- **Purpose**: Audit trail and debugging

### 2. **Status Tracker Lambda** (`status_tracker`)
- **Purpose**: Update DynamoDB at each step
- **Actions**: `start`, `step_update`, `complete`, `fail`
- **Tracks**: What step is running, success/failure, timing

### 3. **Completion Notifier Lambda** (`completion_notifier`)
- **Purpose**: Send Slack notifications when done
- **Sends**: Success message with results OR failure message with error
- **Format**: Rich Slack blocks with project details, links, workspace names

### 4. **DynamoDB Helper Module** (`dynamodb_helper.py`)
- **Shared code**: Reusable DynamoDB operations
- **Functions**: Create records, update status, query executions, get logs
- **Handles**: Type conversion (floats → Decimals), TTL, timestamps

### 5. **Enhanced Step Functions**
- **New file**: `step_functions_with_tracking.tf`
- **Adds**: Status tracking after each step
- **Tracks**: Initialize → Each step → Complete/Fail → Notify
- **Resilient**: Continues even if tracking fails

## Data Structure

### Execution Record (Stored in DynamoDB)

```json
{
  "execution_id": "abc123",
  "status": "RUNNING | SUCCEEDED | FAILED",
  "current_step": "CreateWorkspaces",
  "project_name": "EMS",
  "slack_channel": "C0123456789",
  "slack_user": "U0987654321",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:05:00Z",
  "intake_data": { /* full form data */ },
  "steps": {
    "ValidateIntake": {"status": "SUCCEEDED", "started_at": "...", "completed_at": "..."},
    "CreateGitHubBranch": {"status": "SUCCEEDED", ...},
    "CommitToGitHub": {"status": "RUNNING", "started_at": "..."},
    "CreateHCPProject": {"status": "PENDING"},
    "CreateWorkspaces": {"status": "PENDING"},
    "ConfigureVariables": {"status": "PENDING"}
  },
  "results": {
    "project_id": "prj-abc123",
    "file_url": "https://github.com/...",
    "workspaces": { /* workspace IDs and names */ }
  }
}
```

## How It Works

```
User submits form
    ↓
Step Functions starts
    ↓
InitializeTracking → DynamoDB record created
    ↓
ValidateIntake
    ↓
TrackValidationSuccess → DynamoDB updated
    ↓
CreateGitHubBranch
    ↓
TrackGitHubBranchSuccess → DynamoDB updated
    ↓
... (each step tracked) ...
    ↓
TrackCompletion → Mark as SUCCEEDED
    ↓
NotifySuccess → Slack message sent
```

**If any step fails:**
```
Step fails
    ↓
TrackStepFailure → DynamoDB updated with error
    ↓
TrackFailure → Mark execution as FAILED
    ↓
NotifyFailure → Slack error message sent
```

## Query Examples

### Get execution status
```python
from dynamodb_helper import get_helper

db = get_helper()
execution = db.get_execution('abc123-def456')
print(f"Status: {execution['status']}, Step: {execution['current_step']}")
```

### Get recent jobs in channel
```python
executions = db.get_executions_by_channel('C0123456789', limit=10)
for e in executions:
    print(f"{e['project_name']}: {e['status']}")
```

### Find all running jobs
```python
running_jobs = db.get_executions_by_status('RUNNING')
print(f"Found {len(running_jobs)} jobs in progress")
```

### Get detailed logs
```python
logs = db.get_execution_logs('abc123-def456')
for log in logs:
    print(f"[{log['log_time']}] {log['step_name']}: {log['status']}")
```

### Query via AWS CLI
```bash
# Get execution
aws dynamodb get-item \
  --table-name det-onboarding-prod-executions \
  --key '{"execution_id": {"S": "abc123-def456"}}'

# Query by channel
aws dynamodb query \
  --table-name det-onboarding-prod-executions \
  --index-name slack-channel-index \
  --key-condition-expression "slack_channel = :channel" \
  --expression-attribute-values '{":channel": {"S": "C0123456789"}}'
```

## Deployment

The new components are automatically deployed with Terraform:

```bash
cd terraform
terraform init
terraform apply
```

**What gets created:**
- 2 DynamoDB tables (with indexes, TTL, streams)
- 2 new Lambda functions (status_tracker, completion_notifier)
- Updated Step Functions state machine
- Updated IAM permissions
- CloudWatch log groups

## Benefits

### 1. **Real-time Visibility**
- See exactly which step is running
- Know when each step started/completed
- View execution history in DynamoDB

### 2. **Complete Audit Trail**
- Every state transition logged with timestamp
- Full intake data preserved
- Results from each step stored
- Error messages captured

### 3. **Easy Troubleshooting**
- Query failed executions: `status = FAILED`
- See which step failed
- Get error message from DynamoDB
- Review detailed logs

### 4. **Slack Notifications**
- Automatic success message with links
- Automatic failure alerts with errors
- Rich formatting with workspace details

### 5. **Analytics Ready**
- Query by project, channel, status
- Calculate success rates
- Measure execution times
- Track workspace creation counts

## File Changes

```
New files created:
├── lambda_functions/
│   ├── status_tracker/handler.py          ✅ Status tracking Lambda
│   ├── completion_notifier/handler.py      ✅ Slack notification Lambda
│   └── shared_layer/python/
│       └── dynamodb_helper.py              ✅ DynamoDB operations
│
├── terraform/
│   ├── dynamodb.tf                         📝 Updated with new table
│   ├── lambda_status_tracking.tf           ✅ New Lambda configs
│   ├── step_functions_with_tracking.tf     ✅ Enhanced state machine
│   ├── iam.tf                              📝 Updated permissions
│   └── outputs.tf                          📝 Updated outputs
│
└── docs/
    └── dynamodb-status-tracking.md         ✅ Detailed documentation

Legend: ✅ New | 📝 Updated
```

## Cost Impact

Additional cost for 1,000 executions/month: **~$3.29**

| Component | Cost |
|-----------|------|
| DynamoDB writes (executions) | $1.25 |
| DynamoDB writes (logs) | $1.88 |
| DynamoDB reads | $0.03 |
| Storage | $0.13 |
| Lambda (status_tracker) | ~$0.05 |
| Lambda (completion_notifier) | ~$0.05 |
| **Total** | **~$3.39/month** |

Previous total: $2.24 → New total: **$5.63/month** for 1,000 jobs

## Usage in Slack App

No code changes needed in `main_with_api_gateway.py` - tracking happens automatically!

The Step Functions workflow tracks everything:
1. Execution starts → Record created
2. Each step runs → Status updated
3. Workflow completes → Slack notified
4. Any failure → Error logged + Slack alerted

## Monitoring

### Check job status
```bash
# View executions table
aws dynamodb scan \
  --table-name det-onboarding-prod-executions \
  --limit 5

# View logs table
aws dynamodb scan \
  --table-name det-onboarding-prod-execution-logs \
  --limit 10
```

### CloudWatch Logs
```bash
# Status tracker logs
aws logs tail /aws/lambda/det-onboarding-prod-status-tracker --follow

# Notifier logs
aws logs tail /aws/lambda/det-onboarding-prod-completion-notifier --follow
```

## Key Features Summary

✅ **Complete intake data storage** - Every field from the form saved  
✅ **Step-by-step tracking** - Know exactly where execution is  
✅ **Automatic Slack notifications** - Success & failure messages  
✅ **Query by channel/project/status** - Find jobs easily  
✅ **90-day retention with TTL** - Auto-cleanup old records  
✅ **Detailed audit logs** - Millisecond precision timestamps  
✅ **3 Global Secondary Indexes** - Fast queries by channel, project, status  
✅ **Point-in-time recovery** - 35-day backup  
✅ **DynamoDB Streams** - Real-time change capture  
✅ **Resilient tracking** - Workflow continues even if tracking fails  

## Next Steps

1. **Deploy**: Run `terraform apply` to create tables and Lambda functions
2. **Test**: Submit a form via Slack and check DynamoDB
3. **Query**: Use `dynamodb_helper.py` to query execution status
4. **Monitor**: Check CloudWatch Logs for tracking events
5. **Integrate**: Build dashboards using DynamoDB data

## Documentation

- **Detailed guide**: [docs/dynamodb-status-tracking.md](docs/dynamodb-status-tracking.md)
- **Architecture**: [docs/step-functions-architecture.md](docs/step-functions-architecture.md)
- **Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Quick start**: [QUICK_START.md](QUICK_START.md)

---

**Summary**: Added complete job tracking with DynamoDB for status monitoring, audit trails, and Slack notifications. All automatic. ~$3.39/month for 1,000 jobs.
