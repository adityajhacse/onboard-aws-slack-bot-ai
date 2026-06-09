# Terraform Deployment Guide

## New Lambda Functions Added

This deployment adds two new Lambda functions to your infrastructure:

1. **`status_lookup`** - API endpoint for Service Request ID lookups
2. **`validation_notifier`** - Sends immediate Slack notifications after validation

## Pre-Deployment Checklist

- [ ] Terraform >= 1.5.0 installed
- [ ] AWS CLI configured with correct credentials
- [ ] All environment variables set in `terraform.tfvars`
- [ ] Review `terraform/modules/lambda/lambda_functions/` to ensure new functions exist:
  - `status_lookup/handler.py`
  - `validation_notifier/handler.py`

---

## Deployment Steps

### Step 1: Initialize Terraform (if first time)

```bash
cd terraform
terraform init
```

### Step 2: Review the Plan

```bash
terraform plan
```

**Expected new resources:**
- 2 new Lambda functions (status_lookup, validation_notifier)
- 2 new CloudWatch log groups
- 1 new API Gateway method (GET /status)
- 1 Lambda permission for API Gateway
- Updated API Gateway deployment

**Total new resources:** ~6-8

### Step 3: Apply the Changes

```bash
terraform apply
```

Type `yes` when prompted.

### Step 4: Get the Status API URL

After successful deployment:

```bash
terraform output status_api_url
```

Copy this URL - you'll need it for the Slack bot.

Example output:
```
status_api_url = "https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/status"
```

---

## Configure Slack Bot

Set the environment variable on your Slack bot server:

```bash
export STATUS_API_URL="https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/status"
```

Or add to `.env`:
```
STATUS_API_URL=https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/status
```

Restart the bot:
```bash
cd /path/to/src
python3 main_with_api_gateway.py
```

---

## Verify Deployment

### Test 1: Check Lambda Functions

```bash
aws lambda list-functions --query 'Functions[?contains(FunctionName, `status-lookup`)]'
aws lambda list-functions --query 'Functions[?contains(FunctionName, `validation-notifier`)]'
```

### Test 2: Test Status API Directly

```bash
# Replace with your actual API URL and a real Service Request ID
curl "https://YOUR_API_URL/status?service_request_id=SR-20260608-1408"
```

Expected response:
```json
{
  "service_request_id": "SR-20260608-1408",
  "project_name": "DEV101",
  "status": "SUCCEEDED",
  "steps": {...}
}
```

### Test 3: Test in Slack

```
/aws-det-onboard-status SR-20260608-1408
```

Should show formatted status with all pipeline steps.

---

## Terraform Outputs

After deployment, these outputs are available:

```bash
# Get all outputs
terraform output

# Get specific output
terraform output status_api_url
terraform output lambda_function_arns
```

**Key outputs:**
- `status_api_url` - Status API endpoint for Slack bot
- `api_gateway_url` - Main API Gateway endpoint
- `lambda_function_arns` - All Lambda function ARNs (including new ones)

---

## Rollback

If you need to rollback:

### Option 1: Terraform Rollback (Recommended)

```bash
cd terraform
git checkout HEAD~1  # Go back to previous commit
terraform apply
```

### Option 2: Manual Removal

```bash
# Remove status lookup resources
aws lambda delete-function --function-name det-onboarding-prod-status-lookup
aws lambda delete-function --function-name det-onboarding-prod-validation-notifier

# Re-deploy API Gateway
cd terraform
terraform apply
```

---

## Troubleshooting

### Issue: "Error creating Lambda function"

**Cause:** Handler file not found

**Solution:**
```bash
# Check files exist
ls terraform/modules/lambda/lambda_functions/status_lookup/handler.py
ls terraform/modules/lambda/lambda_functions/validation_notifier/handler.py
```

### Issue: "Invalid invoke_arn"

**Cause:** Lambda output not properly configured

**Solution:**
```bash
# Check Lambda module outputs
terraform state show module.lambda.aws_lambda_function.status_lookup
```

### Issue: API Gateway returns 403

**Cause:** Lambda permission missing

**Solution:**
```bash
# Check Lambda permission
aws lambda get-policy --function-name det-onboarding-prod-status-lookup
```

Should show API Gateway principal permission.

### Issue: "Module not found: requests"

**Cause:** Shared layer doesn't include requests

**Solution:** The Lambda uses the shared layer which should have all dependencies. If missing, update the shared layer:

```bash
cd terraform/modules/lambda/lambda_functions/shared_layer
pip install requests -t python/
terraform apply
```

---

## Cost Impact

### New Resources Cost (Monthly)

Based on 1,000 status lookups per month:

| Resource | Cost |
|----------|------|
| status_lookup Lambda | $0.001 |
| validation_notifier Lambda | $0.001 |
| API Gateway requests (1,000) | $0.0035 |
| CloudWatch Logs | $0.01 |
| **Total Additional** | **~$0.02/month** |

**Negligible cost increase!**

---

## Next Steps After Deployment

1. ✅ Verify all Terraform resources created
2. ✅ Get status_api_url from outputs
3. ✅ Configure Slack bot with STATUS_API_URL
4. ✅ Restart Slack bot
5. ✅ Test `/aws-det-onboard-status` command
6. ✅ Monitor CloudWatch logs for any errors
7. ✅ Submit test onboarding request to verify end-to-end

---

## Additional Configuration (Optional)

### Add API Key (Recommended for Production)

```hcl
# In terraform/modules/api_gateway/main.tf
resource "aws_api_gateway_api_key" "status" {
  name = "${var.name_prefix}-status-api-key"
}

resource "aws_api_gateway_usage_plan" "status" {
  name = "${var.name_prefix}-status-usage-plan"

  api_stages {
    api_id = aws_api_gateway_rest_api.onboarding.id
    stage  = aws_api_gateway_stage.onboarding.stage_name
  }

  throttle_settings {
    burst_limit = 100
    rate_limit  = 50
  }
}

resource "aws_api_gateway_usage_plan_key" "status" {
  key_id        = aws_api_gateway_api_key.status.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.status.id
}

# Update method to require API key
resource "aws_api_gateway_method" "status_lookup_get" {
  # ...
  api_key_required = true
}
```

Then update bot to use API key:
```python
# In status_api_client.py
headers = {'x-api-key': os.environ.get('STATUS_API_KEY')}
response = requests.get(url, params=params, headers=headers)
```

---

## Monitoring

### CloudWatch Dashboards

After deployment, monitor:

```bash
# Status lookup Lambda logs
aws logs tail /aws/lambda/det-onboarding-prod-status-lookup --follow

# Validation notifier Lambda logs
aws logs tail /aws/lambda/det-onboarding-prod-validation-notifier --follow

# API Gateway logs
aws logs tail /aws/apigateway/det-onboarding-prod --follow
```

### Metrics to Watch

- Lambda invocation count
- Lambda error rate
- API Gateway 4xx/5xx errors
- Lambda duration
- DynamoDB read throttles

---

## Success Criteria

After deployment, verify:

- [x] `terraform apply` completed without errors
- [x] All new Lambda functions exist in AWS
- [x] API Gateway has GET /status endpoint
- [x] Status API URL is accessible
- [x] Slack bot can query status successfully
- [x] Service Request IDs are being generated
- [x] Status lookups return correct data

---

**Deployment Complete!** 🎉

Your infrastructure now supports:
- ✅ Service Request ID generation
- ✅ Immediate validation notifications
- ✅ Status lookup via API
- ✅ `/aws-det-onboard-status` Slack command

Time to test it out!
