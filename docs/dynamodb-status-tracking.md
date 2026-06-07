# DynamoDB Status Tracking

## Overview

The DET onboarding workflow uses two DynamoDB tables to track execution status, store service records, and maintain detailed logs of each step.

## Tables

### 1. Executions Table (`det-onboarding-prod-executions`)

**Purpose**: Store complete service records and overall job status.

#### Schema

| Attribute | Type | Description |
|-----------|------|-------------|
| `execution_id` | String (PK) | Unique execution identifier from Step Functions |
| `status` | String | Current status: `RUNNING`, `SUCCEEDED`, `FAILED` |
| `current_step` | String | Name of currently executing step |
| `project_name` | String | Project name from intake |
| `project_slug` | String | URL-safe project identifier |
| `slack_channel` | String | Slack channel ID |
| `slack_user` | String | Slack user ID who initiated |
| `created_at` | String (ISO) | Timestamp when execution started |
| `updated_at` | String (ISO) | Last update timestamp |
| `completed_at` | String (ISO) | Timestamp when execution completed |
| `ttl` | Number | TTL for auto-deletion (90 days) |
| `intake_data` | Map | Complete intake form data |
| `steps` | Map | Status of each step (see below) |
| `results` | Map | Results from each step |
| `error_message` | String | Error message if failed |

#### Steps Map Structure

```json
{
  "ValidateIntake": {
    "status": "SUCCEEDED",
    "started_at": "2024-01-01T10:00:00Z",
    "completed_at": "2024-01-01T10:00:05Z",
    "result": { ... }
  },
  "CreateGitHubBranch": {
    "status": "SUCCEEDED",
    "started_at": "2024-01-01T10:00:05Z",
    "completed_at": "2024-01-01T10:00:10Z",
    "result": "ems-project"
  },
  "CommitToGitHub": {
    "status": "SUCCEEDED",
    "started_at": "2024-01-01T10:00:10Z",
    "completed_at": "2024-01-01T10:00:15Z",
    "result": {
      "file_url": "https://github.com/...",
      "commit_sha": "abc123..."
    }
  },
  "CreateHCPProject": {
    "status": "RUNNING",
    "started_at": "2024-01-01T10:00:15Z"
  },
  "CreateWorkspaces": {
    "status": "PENDING"
  },
  "ConfigureVariables": {
    "status": "PENDING"
  }
}
```

#### Global Secondary Indexes

1. **slack-channel-index**
   - Partition Key: `slack_channel`
   - Sort Key: `created_at`
   - Purpose: Query executions by Slack channel

2. **project-name-index**
   - Partition Key: `project_name`
   - Sort Key: `created_at`
   - Purpose: Query executions by project name

3. **status-index**
   - Partition Key: `status`
   - Sort Key: `created_at`
   - Purpose: Find all running/failed jobs

#### Example Record

```json
{
  "execution_id": "abc123-def456",
  "status": "SUCCEEDED",
  "current_step": "ConfigureVariables",
  "project_name": "EMS",
  "project_slug": "ems",
  "slack_channel": "C0123456789",
  "slack_user": "U0987654321",
  "created_at": "2024-01-01T10:00:00.000Z",
  "updated_at": "2024-01-01T10:05:00.000Z",
  "completed_at": "2024-01-01T10:05:00.000Z",
  "ttl": 1711969200,
  "intake_data": {
    "project_name": "EMS",
    "terraform_repo": "my-org/terraform-ems",
    "environments": ["Dev", "QA", "Prod"],
    "regions": ["us-east-1"],
    "vpc_model": "Small",
    "service_name": "EMS API",
    "business_justification": "New workload onboarding",
    "team_dl": "ems-team@example.com"
  },
  "steps": {
    "ValidateIntake": {
      "status": "SUCCEEDED",
      "started_at": "2024-01-01T10:00:00Z",
      "completed_at": "2024-01-01T10:00:05Z"
    },
    "CreateGitHubBranch": {
      "status": "SUCCEEDED",
      "started_at": "2024-01-01T10:00:05Z",
      "completed_at": "2024-01-01T10:00:10Z"
    },
    "CommitToGitHub": {
      "status": "SUCCEEDED",
      "started_at": "2024-01-01T10:00:10Z",
      "completed_at": "2024-01-01T10:00:15Z"
    },
    "CreateHCPProject": {
      "status": "SUCCEEDED",
      "started_at": "2024-01-01T10:00:15Z",
      "completed_at": "2024-01-01T10:00:20Z"
    },
    "CreateWorkspaces": {
      "status": "SUCCEEDED",
      "started_at": "2024-01-01T10:00:20Z",
      "completed_at": "2024-01-01T10:04:00Z"
    },
    "ConfigureVariables": {
      "status": "SUCCEEDED",
      "started_at": "2024-01-01T10:04:00Z",
      "completed_at": "2024-01-01T10:05:00Z"
    }
  },
  "results": {
    "project_id": "prj-abc123",
    "project_name": "EMS",
    "file_url": "https://github.com/my-org/terraform-ems/blob/ems-project/requests/ems-dev.json",
    "branch_name": "ems-project",
    "workspaces": {
      "Dev": {
        "workspace_id": "ws-dev123",
        "workspace_name": "ems-dev",
        "success": true,
        "created_at": "2024-01-01T10:02:00Z"
      },
      "QA": {
        "workspace_id": "ws-qa456",
        "workspace_name": "ems-qa",
        "success": true,
        "created_at": "2024-01-01T10:02:05Z"
      },
      "Prod": {
        "workspace_id": "ws-prod789",
        "workspace_name": "ems-prod",
        "success": true,
        "created_at": "2024-01-01T10:02:10Z"
      }
    }
  }
}
```

### 2. Execution Logs Table (`det-onboarding-prod-execution-logs`)

**Purpose**: Store detailed step-by-step logs with timestamps.

#### Schema

| Attribute | Type | Description |
|-----------|------|-------------|
| `execution_id` | String (PK) | Execution identifier |
| `timestamp` | Number (SK) | Unix timestamp in milliseconds |
| `step_name` | String | Name of the step |
| `status` | String | Step status |
| `log_time` | String (ISO) | Human-readable timestamp |
| `result` | Map | Optional result data |
| `error` | String | Optional error message |
| `ttl` | Number | TTL for auto-deletion (90 days) |

#### Global Secondary Indexes

1. **step-name-index**
   - Partition Key: `step_name`
   - Sort Key: `timestamp`
   - Purpose: Query logs by step name across executions

#### Example Log Entries

```json
[
  {
    "execution_id": "abc123-def456",
    "timestamp": 1704103200000,
    "step_name": "ValidateIntake",
    "status": "RUNNING",
    "log_time": "2024-01-01T10:00:00.000Z",
    "ttl": 1711969200
  },
  {
    "execution_id": "abc123-def456",
    "timestamp": 1704103205000,
    "step_name": "ValidateIntake",
    "status": "SUCCEEDED",
    "log_time": "2024-01-01T10:00:05.000Z",
    "result": {
      "valid": true,
      "project_name": "EMS"
    },
    "ttl": 1711969200
  },
  {
    "execution_id": "abc123-def456",
    "timestamp": 1704103205100,
    "step_name": "CreateGitHubBranch",
    "status": "RUNNING",
    "log_time": "2024-01-01T10:00:05.100Z",
    "ttl": 1711969200
  }
]
```

## Usage Examples

### Query Execution Status

```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('det-onboarding-prod-executions')

# Get by execution ID
response = table.get_item(Key={'execution_id': 'abc123-def456'})
execution = response.get('Item')

print(f"Status: {execution['status']}")
print(f"Current Step: {execution['current_step']}")
print(f"Project: {execution['project_name']}")
```

### Query by Slack Channel

```python
# Get recent executions in a channel
response = table.query(
    IndexName='slack-channel-index',
    KeyConditionExpression='slack_channel = :channel',
    ExpressionAttributeValues={':channel': 'C0123456789'},
    ScanIndexForward=False,  # Most recent first
    Limit=10
)

for item in response['Items']:
    print(f"{item['project_name']}: {item['status']} ({item['created_at']})")
```

### Query Running Jobs

```python
# Find all currently running jobs
response = table.query(
    IndexName='status-index',
    KeyConditionExpression='#status = :status',
    ExpressionAttributeNames={'#status': 'status'},
    ExpressionAttributeValues={':status': 'RUNNING'},
    ScanIndexForward=False,
    Limit=100
)

running_jobs = response['Items']
print(f"Found {len(running_jobs)} running jobs")
```

### Query Execution Logs

```python
logs_table = dynamodb.Table('det-onboarding-prod-execution-logs')

# Get logs for a specific execution
response = logs_table.query(
    KeyConditionExpression='execution_id = :exec_id',
    ExpressionAttributeValues={':exec_id': 'abc123-def456'},
    ScanIndexForward=True  # Chronological order
)

for log in response['Items']:
    print(f"[{log['log_time']}] {log['step_name']}: {log['status']}")
```

### Query by Step Name

```python
# Find all CreateWorkspaces executions
response = logs_table.query(
    IndexName='step-name-index',
    KeyConditionExpression='step_name = :step',
    ExpressionAttributeValues={':step': 'CreateWorkspaces'},
    ScanIndexForward=False,
    Limit=100
)

for log in response['Items']:
    print(f"{log['execution_id']}: {log['status']}")
```

## Status Tracking in Step Functions

The workflow automatically tracks status at each step:

1. **InitializeTracking**: Creates initial record with intake data
2. **After each step**: Updates step status (RUNNING → SUCCEEDED/FAILED)
3. **TrackCompletion**: Marks execution as SUCCEEDED with final results
4. **TrackFailure**: Marks execution as FAILED with error message

## Slack Notifications

The `completion_notifier` Lambda sends Slack messages when workflows complete:

### Success Notification

```
🎉 Onboarding Complete: EMS

Requested by: @user
Execution ID: abc123-def456

✅ Project: EMS
✅ HCP Terraform Project ID: prj-abc123
✅ GitHub Branch: ems-project
✅ GitHub File: https://github.com/...
✅ Workspaces Created: ems-dev, ems-qa, ems-prod
```

### Failure Notification

```
❌ Onboarding Failed: EMS

Requested by: @user
Execution ID: abc123-def456

Error:
Failed to create GitHub branch after 3 retries

Check AWS Step Functions console for detailed execution history.
```

## Data Retention

- **TTL**: 90 days (automatically deleted)
- **Point-in-time recovery**: Enabled (35 days backup)
- **Streams**: Enabled for change data capture

## Monitoring

### CloudWatch Metrics

- Read/Write capacity units
- Throttled requests
- System errors

### CloudWatch Alarms

- Read throttle events (threshold: 10 in 5 min)
- Write throttle events (threshold: 10 in 5 min)

## Cost Estimation

For 1,000 executions per month:

| Operation | Count | Cost |
|-----------|-------|------|
| Writes (executions table) | ~10 per execution | ~$1.25 |
| Writes (logs table) | ~15 per execution | ~$1.88 |
| Reads (status queries) | ~100 per month | ~$0.03 |
| Storage (3 months avg) | ~500 MB | ~$0.13 |
| **Total** | | **~$3.29/month** |

## Best Practices

1. **Query by GSI**: Use indexes for efficient queries
2. **Limit results**: Always use `Limit` parameter
3. **Handle pagination**: Use `LastEvaluatedKey` for large result sets
4. **Cache frequently accessed data**: Use ElastiCache if needed
5. **Monitor capacity**: Watch for throttling in CloudWatch
6. **Archive old data**: Export to S3 before TTL deletion if needed

## API Examples

### REST API Query

```bash
# Get execution status
aws dynamodb get-item \
  --table-name det-onboarding-prod-executions \
  --key '{"execution_id": {"S": "abc123-def456"}}'

# Query by channel
aws dynamodb query \
  --table-name det-onboarding-prod-executions \
  --index-name slack-channel-index \
  --key-condition-expression "slack_channel = :channel" \
  --expression-attribute-values '{":channel": {"S": "C0123456789"}}' \
  --limit 10
```

### Python SDK (boto3)

```python
from dynamodb_helper import get_helper

db = get_helper()

# Get execution
execution = db.get_execution('abc123-def456')

# Get recent executions for a channel
executions = db.get_executions_by_channel('C0123456789', limit=10)

# Get running jobs
running = db.get_executions_by_status('RUNNING')

# Get execution logs
logs = db.get_execution_logs('abc123-def456')
```

## Troubleshooting

### Issue: Throttled Requests

**Solution**: 
1. Check CloudWatch alarms
2. Switch to provisioned capacity if sustained load
3. Implement exponential backoff in queries

### Issue: Large Item Size

**Solution**:
- DynamoDB item limit: 400 KB
- Store large data in S3, keep reference in DynamoDB
- Compress intake data if needed

### Issue: Query Performance

**Solution**:
1. Use GSIs for common query patterns
2. Add pagination for large result sets
3. Consider DynamoDB Streams + Lambda for real-time updates

## Security

- **Encryption**: At rest (AWS managed keys)
- **Access control**: IAM policies with least privilege
- **Audit**: CloudTrail logs all API calls
- **VPC**: Can deploy in VPC for additional security
