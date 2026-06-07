# Refactor: Slack Bot Runs Locally, Executes via Lambda

## Current Problem

Currently, the Slack bot (`src/main_with_api_gateway.py`) executes some operations **locally**:

### Local Executions (❌ Need to Move to Lambda)
- **Line 432**: `list_org_repositories()` - Lists GitHub repos for dropdown
- **AI orchestrator** - Entire AI chat orchestration
- **Intake validation** - Form validation
- **MCP server** - Local MCP operations

### Already Using Lambda (✅ Correct)
- **Line 478**: `api_client.trigger_onboarding()` - Triggers Step Functions via API Gateway

---

## Goal: Move ALL Business Logic to Lambda

**Desired Architecture:**
```
Slack Bot (Local)
    ↓ (ALL operations via Lambda)
    API Gateway → Lambda Functions
```

---

## Solution: Create Additional Lambda Functions + API Endpoints

### 1. New Lambda Functions Needed

#### A. **list_repositories** Lambda
**Purpose:** Lists GitHub repositories for Slack modal dropdown

**Handler:** `lambda_functions/list_repositories/handler.py`
```python
import json
import os
from github_api import list_org_repositories, GitHubApiError

def lambda_handler(event, context):
    """List GitHub repositories for Slack dropdown"""
    try:
        body = json.loads(event.get('body', '{}'))
        query = body.get('query', '')
        limit = body.get('limit', 100)
        
        owner = os.environ['GITHUB_OWNER']
        token = os.environ['GITHUB_TOKEN']
        
        repos = list_org_repositories(owner, token, query=query, limit=limit)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'repos': repos
            })
        }
    except GitHubApiError as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
```

#### B. **validate_intake_form** Lambda
**Purpose:** Validates intake form data before submission

**Handler:** `lambda_functions/validate_intake_form/handler.py`
```python
import json
from det_intake import validate_intake

def lambda_handler(event, context):
    """Validate intake form data"""
    try:
        body = json.loads(event.get('body', '{}'))
        intake = body.get('intake', {})
        
        validation_result = validate_intake(intake)
        
        return {
            'statusCode': 200,
            'body': json.dumps(validation_result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'valid': False,
                'errors': [str(e)]
            })
        }
```

#### C. **ai_orchestrate** Lambda
**Purpose:** Handles AI chat orchestration

**Handler:** `lambda_functions/ai_orchestrate/handler.py`
```python
import json
from ai_orchestrator import DetChatOrchestrator

# Create global orchestrator (reused across invocations)
orchestrator = DetChatOrchestrator()

def lambda_handler(event, context):
    """Handle AI chat orchestration"""
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')  # 'message', 'approve', 'cancel'
        
        if action == 'message':
            response = orchestrator.handle_message(
                team_id=body.get('team_id'),
                channel_id=body.get('channel_id'),
                user_id=body.get('user_id'),
                thread_ts=body.get('thread_ts'),
                text=body.get('text'),
                slack_user=body.get('slack_user')
            )
        elif action == 'approve':
            response = orchestrator.approve(
                session_key=body.get('session_key'),
                slack_user=body.get('slack_user')
            )
        elif action == 'cancel':
            response = orchestrator.cancel(
                session_key=body.get('session_key')
            )
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid action'})
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'text': response.text,
                'blocks': response.blocks
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

---

### 2. New API Gateway Endpoints

Add these endpoints to `modules/api_gateway/main.tf`:

```hcl
# GET /repositories
resource "aws_api_gateway_resource" "repositories" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  parent_id   = aws_api_gateway_rest_api.onboarding.root_resource_id
  path_part   = "repositories"
}

# POST /validate
resource "aws_api_gateway_resource" "validate" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  parent_id   = aws_api_gateway_rest_api.onboarding.root_resource_id
  path_part   = "validate"
}

# POST /ai-orchestrate
resource "aws_api_gateway_resource" "ai_orchestrate" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  parent_id   = aws_api_gateway_rest_api.onboarding.root_resource_id
  path_part   = "ai-orchestrate"
}
```

---

### 3. Updated `api_gateway_client.py`

Add methods to call new Lambda functions:

```python
# src/api_gateway_client.py

class ApiGatewayClient:
    def __init__(self):
        self.base_url = os.environ.get("API_GATEWAY_ENDPOINT", "").rstrip("/")
        if not self.base_url:
            raise ApiGatewayError("API_GATEWAY_ENDPOINT not configured")
    
    def list_repositories(self, query="", limit=100):
        """List GitHub repositories via Lambda"""
        url = f"{self.base_url}/repositories"
        payload = {"query": query, "limit": limit}
        
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code != 200:
            raise ApiGatewayError(f"Failed to list repositories: {response.text}")
        
        data = response.json()
        return data.get("repos", [])
    
    def validate_intake(self, intake):
        """Validate intake data via Lambda"""
        url = f"{self.base_url}/validate"
        payload = {"intake": intake}
        
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code != 200:
            raise ApiGatewayError(f"Failed to validate intake: {response.text}")
        
        return response.json()
    
    def ai_orchestrate(self, action, **kwargs):
        """Call AI orchestrator via Lambda"""
        url = f"{self.base_url}/ai-orchestrate"
        payload = {"action": action, **kwargs}
        
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code != 200:
            raise ApiGatewayError(f"AI orchestration failed: {response.text}")
        
        return response.json()
```

---

### 4. Updated Slack Bot (`main_with_api_gateway.py`)

Replace local calls with API Gateway calls:

#### Before (Line 432):
```python
try:
    repos = list_org_repositories(owner, token, query=query, limit=100)
except GitHubApiError as exc:
    logger.warning("Could not load terraform repo options: %s", exc)
    ack(options=[])
    return
```

#### After:
```python
try:
    repos = api_client.list_repositories(query=query, limit=100)
except ApiGatewayError as exc:
    logger.warning("Could not load terraform repo options: %s", exc)
    ack(options=[])
    return
```

#### Before (AI orchestrator - Line 98-106):
```python
response = chat_orchestrator.handle_message(
    team_id=team_id,
    channel_id=channel_id,
    user_id=user_id,
    thread_ts="default",
    text=text,
    slack_user={"id": user_id},
)
```

#### After:
```python
response_data = api_client.ai_orchestrate(
    action="message",
    team_id=team_id,
    channel_id=channel_id,
    user_id=user_id,
    thread_ts="default",
    text=text,
    slack_user={"id": user_id},
)
# Convert to response object
response = ChatResponse(
    text=response_data['text'],
    blocks=response_data.get('blocks')
)
```

---

## Benefits of This Approach

### ✅ Advantages

1. **Slack Bot is Thin Client**
   - Only handles Slack protocol (events, modals, buttons)
   - No business logic
   - Easy to test and maintain

2. **All Logic in Lambda**
   - Centralized business logic
   - Scalable (Lambda auto-scales)
   - Can be invoked from multiple sources (Slack, API, CLI)

3. **Consistent Execution Environment**
   - Same code runs in Lambda (no local vs deployed differences)
   - Same environment variables
   - Same dependencies

4. **Better Monitoring**
   - All operations logged in CloudWatch
   - Complete audit trail
   - Easy to debug

5. **Security**
   - Tokens stay in AWS (Lambda environment variables)
   - No local token storage needed for bot

---

## Implementation Steps

### Phase 1: Add New Lambda Functions

1. **Create Lambda function code:**
   ```bash
   mkdir -p terraform/modules/lambda/lambda_functions/list_repositories
   mkdir -p terraform/modules/lambda/lambda_functions/validate_intake_form
   mkdir -p terraform/modules/lambda/lambda_functions/ai_orchestrate
   ```

2. **Create handlers** (see examples above)

3. **Update `modules/lambda/main.tf`** to add new functions

### Phase 2: Add API Gateway Endpoints

1. **Update `modules/api_gateway/main.tf`** with new resources
2. **Add Lambda integrations** for each endpoint
3. **Configure CORS** for browser calls (if needed)

### Phase 3: Update Slack Bot

1. **Update `api_gateway_client.py`** with new methods
2. **Replace local calls** in `main_with_api_gateway.py`
3. **Remove unused imports** (`from github_api import ...`, etc.)

### Phase 4: Deploy

```bash
cd terraform
terraform apply
```

### Phase 5: Update Slack Bot Environment

```bash
# Only need Slack tokens now
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
export API_GATEWAY_ENDPOINT="https://...execute-api.../prod"

# No longer need these locally:
# export GITHUB_TOKEN="..."
# export HCP_TERRAFORM_TOKEN="..."
# export OPENAI_API_KEY="..."
```

### Phase 6: Test

1. Start Slack bot: `./start_slack_bot.sh`
2. Test repository dropdown
3. Test AI orchestration
4. Test full onboarding workflow

---

## Trade-offs

### Pros
- ✅ Slack bot is lightweight
- ✅ All logic centralized in Lambda
- ✅ Better security (tokens in AWS)
- ✅ Scalable
- ✅ Consistent environment

### Cons
- ❌ Additional latency (network calls to Lambda)
- ❌ More complex debugging (need to check CloudWatch)
- ❌ Lambda cold starts (first call may be slow)
- ❌ More API Gateway costs

---

## Alternative: Hybrid Approach

Keep **fast, simple operations local**, move **heavy operations to Lambda**:

### Keep Local
- ✅ Repository list (fast, cacheable)
- ✅ Input validation (no external calls)
- ✅ Slack UI rendering

### Move to Lambda
- ✅ GitHub operations (branch creation, commits)
- ✅ HCP Terraform operations
- ✅ AI orchestration (heavy, stateful)
- ✅ Full onboarding workflow

This balances performance with centralization.

---

## Recommended Approach

**Option A: Full Lambda Execution** (Your Request)
```
Slack Bot (Local) → API Gateway → Lambda (ALL operations)
```
- Best for: Production systems, multiple Slack bots, security
- Use when: You want complete centralization

**Option B: Hybrid** (Balanced)
```
Slack Bot (Local) → Direct calls for simple ops
                  → API Gateway → Lambda for complex ops
```
- Best for: Development, lower latency, cost optimization
- Use when: You want balance between local and Lambda

---

## Next Steps

Let me know if you want me to:

1. **Implement full Lambda execution** (Option A)
   - Create all new Lambda functions
   - Add API Gateway endpoints
   - Update Slack bot to use API Gateway for everything

2. **Implement hybrid approach** (Option B)
   - Keep simple operations local
   - Move complex operations to Lambda
   - Balance latency vs centralization

3. **Start with specific operations**
   - Which operation should move to Lambda first?
   - Repository list? AI orchestration? Validation?

---

**What would you like to do?** 🚀
