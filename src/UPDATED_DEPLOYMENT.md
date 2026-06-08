# Updated Deployment Guide (API-Based Architecture)

## Architecture Change

**Previous approach:** Slack bot directly queries DynamoDB using boto3  
**New approach:** Slack bot calls API Gateway → Lambda → DynamoDB

**Benefits:**
- ✅ No boto3 dependency in Slack bot
- ✅ Cleaner separation of concerns
- ✅ Can add caching, rate limiting at API layer
- ✅ API can be used by other clients (web dashboard, CLI, etc.)

---

## Components Overview

### 1. Status Lookup Lambda Function
**Location:** `src/status_lookup_lambda/handler.py`
- Queries DynamoDB by Service Request ID
- Returns JSON response via API Gateway
- No Slack dependencies

### 2. Status API Client
**Location:** `src/status_api_client.py`
- HTTP client for Slack bot
- Calls API Gateway
- Formats responses for Slack
- Only dependency: `requests` library

### 3. Updated Slack Bot
**Location:** `src/main_with_api_gateway.py`
- Uses `StatusApiClient` instead of boto3
- No direct AWS SDK dependencies needed

---

## Deployment Steps

### Step 1: Deploy Status Lookup Lambda

Create the Lambda function:

```bash
cd src/status_lookup_lambda
zip function.zip handler.py

# Create Lambda function
aws lambda create-function \
  --function-name det-onboarding-prod-status-lookup \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/YOUR_LAMBDA_ROLE \
  --handler handler.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables="{DYNAMODB_TABLE=det-onboarding-prod-executions}" \
  --layers arn:aws:lambda:REGION:ACCOUNT:layer:shared-layer:VERSION
```

**Note the ARN** - you'll need it for API Gateway.

---

### Step 2: Create API Gateway Endpoint

**Option A: Using AWS Console**

1. Go to API Gateway console
2. Select your existing API or create new REST API
3. Create new resource: `/status`
4. Create GET method on `/status`:
   - Integration type: Lambda Function
   - Lambda Function: `det-onboarding-prod-status-lookup`
   - Use Lambda Proxy integration: ✅ Yes
5. Enable CORS
6. Deploy API to stage (e.g., `prod`)
7. Note the invoke URL: `https://xxxxx.execute-api.REGION.amazonaws.com/prod`

**Option B: Using Terraform**

```hcl
# terraform/modules/api_gateway/status_endpoint.tf

resource "aws_api_gateway_resource" "status" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  parent_id   = aws_api_gateway_rest_api.onboarding.root_resource_id
  path_part   = "status"
}

resource "aws_api_gateway_method" "status_get" {
  rest_api_id   = aws_api_gateway_rest_api.onboarding.id
  resource_id   = aws_api_gateway_resource.status.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "status" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.status.id
  http_method = aws_api_gateway_method.status_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.status_lookup.invoke_arn
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "status_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status_lookup.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.onboarding.execution_arn}/*/*"
}

# Enable CORS
resource "aws_api_gateway_method" "status_options" {
  rest_api_id   = aws_api_gateway_rest_api.onboarding.id
  resource_id   = aws_api_gateway_resource.status.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.status.id
  http_method = aws_api_gateway_method.status_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.status.id
  http_method = aws_api_gateway_method.status_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  resource_id = aws_api_gateway_resource.status.id
  http_method = aws_api_gateway_method.status_options.http_method
  status_code = aws_api_gateway_method_response.status_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}
```

Then deploy:
```bash
cd terraform
terraform apply
```

---

### Step 3: Configure Environment Variable

Set the API URL for the Slack bot:

```bash
export STATUS_API_URL="https://xxxxx.execute-api.REGION.amazonaws.com/prod"
```

Or add to your `.env` file:
```
STATUS_API_URL=https://xxxxx.execute-api.REGION.amazonaws.com/prod
```

---

### Step 4: Install Dependencies

The Slack bot now only needs the `requests` library:

```bash
cd src
pip install requests slack-sdk slack-bolt
```

---

### Step 5: Restart Slack Bot

```bash
cd src

# Ensure environment variables are set
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_APP_TOKEN="xapp-your-token"
export STATUS_API_URL="https://xxxxx.execute-api.us-east-1.amazonaws.com/prod"

# Run the bot
python main_with_api_gateway.py
```

---

## Testing

### Test 1: Test Lambda Function Directly

```bash
# Test the Lambda function
aws lambda invoke \
  --function-name det-onboarding-prod-status-lookup \
  --payload '{"httpMethod":"GET","queryStringParameters":{"service_request_id":"SR-20260608-1234"}}' \
  response.json

cat response.json
```

Expected output:
```json
{
  "statusCode": 200,
  "body": "{\"service_request_id\":\"SR-20260608-1234\",\"status\":\"RUNNING\",...}"
}
```

### Test 2: Test API Gateway Endpoint

```bash
# Test via API Gateway
curl "https://xxxxx.execute-api.REGION.amazonaws.com/prod/status?service_request_id=SR-20260608-1234"
```

Expected response:
```json
{
  "service_request_id": "SR-20260608-1234",
  "project_name": "CustomerAPI",
  "status": "RUNNING",
  "steps": {...}
}
```

### Test 3: Test Slack Command

In Slack:
```
/aws-det-onboard-status SR-20260608-1234
```

Should display formatted status message.

### Test 4: Test API Client Directly

```python
# Test from Python
from status_api_client import StatusApiClient
import os

os.environ['STATUS_API_URL'] = 'https://xxxxx.execute-api.REGION.amazonaws.com/prod'

client = StatusApiClient()
result = client.get_status('SR-20260608-1234')
print(result)
```

---

## API Specification

### GET /status

**Query Parameters:**
- `service_request_id` (required): Service Request ID (e.g., SR-20260608-1234)

**Response (200 OK):**
```json
{
  "service_request_id": "SR-20260608-1234",
  "project_name": "CustomerAPI",
  "status": "RUNNING",
  "created_at": "2026-06-08T10:00:00Z",
  "completed_at": null,
  "time_elapsed_seconds": 125,
  "time_display": "Running for 2m 5s",
  "current_step": "CreateHCPProject",
  "steps": {
    "validate_intake": "SUCCEEDED",
    "github_branch": "SUCCEEDED",
    "github_commit": "SUCCEEDED",
    "hcp_project": "RUNNING",
    "workspaces": "PENDING",
    "variables": "PENDING"
  }
}
```

**Response (404 Not Found):**
```json
{
  "error": "Not found",
  "message": "No execution found for Service Request ID: SR-INVALID-1234",
  "service_request_id": "SR-INVALID-1234"
}
```

**Response (400 Bad Request):**
```json
{
  "error": "Missing service_request_id parameter",
  "message": "Please provide service_request_id in query string or body"
}
```

**Response (500 Internal Server Error):**
```json
{
  "error": "Internal server error",
  "message": "Error details..."
}
```

---

## Monitoring

### API Gateway Metrics

Monitor these CloudWatch metrics:
- `4XXError` - Client errors (invalid requests)
- `5XXError` - Server errors (Lambda failures)
- `Count` - Total requests
- `Latency` - Response time

```bash
# View API Gateway logs
aws logs tail /aws/apigateway/det-onboarding --follow
```

### Lambda Metrics

```bash
# View Lambda logs
aws logs tail /aws/lambda/det-onboarding-prod-status-lookup --follow
```

### Bot Logs

```bash
# Check bot logs for API calls
grep "Fetching status" bot.log
grep "API returned" bot.log
```

---

## Troubleshooting

### Issue: Bot shows "STATUS_API_URL not configured"

**Solution:** Set the environment variable:
```bash
export STATUS_API_URL="https://xxxxx.execute-api.REGION.amazonaws.com/prod"
```

### Issue: API returns 403 Forbidden

**Check:**
1. Lambda permission for API Gateway
2. API Gateway deployment
3. Lambda function exists

```bash
# Check Lambda permission
aws lambda get-policy --function-name det-onboarding-prod-status-lookup
```

### Issue: API returns 500 error

**Check Lambda logs:**
```bash
aws logs tail /aws/lambda/det-onboarding-prod-status-lookup --follow
```

Common causes:
- DynamoDB table name incorrect
- Missing shared layer
- IAM permissions missing

### Issue: Bot shows "API request timed out"

**Increase timeout:**
```python
# In status_api_client.py
response = requests.get(url, params=params, timeout=30)  # Increase from 10
```

---

## Security Considerations

### API Key (Optional but Recommended)

Add API key requirement:

```hcl
resource "aws_api_gateway_api_key" "status_api" {
  name = "det-onboarding-status-api-key"
}

resource "aws_api_gateway_usage_plan" "status_api" {
  name = "det-onboarding-status-usage-plan"

  api_stages {
    api_id = aws_api_gateway_rest_api.onboarding.id
    stage  = aws_api_gateway_stage.prod.stage_name
  }
}

resource "aws_api_gateway_usage_plan_key" "status_api" {
  key_id        = aws_api_gateway_api_key.status_api.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.status_api.id
}

# Update method to require API key
resource "aws_api_gateway_method" "status_get" {
  # ... other config ...
  api_key_required = true
}
```

Then update bot to use API key:
```python
# In status_api_client.py
headers = {'x-api-key': os.environ.get('STATUS_API_KEY')}
response = requests.get(url, params=params, headers=headers, timeout=10)
```

### Rate Limiting

Add throttling to API Gateway:
```hcl
resource "aws_api_gateway_method_settings" "status" {
  rest_api_id = aws_api_gateway_rest_api.onboarding.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  method_path = "*/GET"

  settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }
}
```

---

## Cost Estimate

### Per 1000 Status Checks

| Service | Usage | Cost |
|---------|-------|------|
| API Gateway | 1,000 requests | $0.0035 |
| Lambda | 1,000 invocations × 500ms | $0.001 |
| DynamoDB | 1,000 reads | $0.25 |
| **Total** | | **~$0.25/1000 checks** |

Very cost-effective for status lookups!

---

## Summary

✅ **No more boto3 dependency in Slack bot**  
✅ **Clean API-based architecture**  
✅ **Status API can be used by other clients**  
✅ **Better separation of concerns**  
✅ **Easier to test and monitor**

The new architecture is production-ready and scalable! 🚀
