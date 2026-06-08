# Quick Start Guide

## 🚀 Get Up and Running in 15 Minutes

This guide gets all three features deployed quickly.

---

## Prerequisites

- AWS CLI configured
- Terraform installed (optional)
- Python 3.12+
- Slack bot tokens ready

---

## Step 1: Deploy Status Lookup API (5 mins)

```bash
# 1. Create Lambda function
cd src/status_lookup_lambda
zip function.zip handler.py

aws lambda create-function \
  --function-name det-status-lookup \
  --runtime python3.12 \
  --role YOUR_LAMBDA_ROLE_ARN \
  --handler handler.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --environment Variables="{DYNAMODB_TABLE=det-onboarding-prod-executions}" \
  --layers YOUR_SHARED_LAYER_ARN

# 2. Note the Lambda ARN from output

# 3. Create API Gateway endpoint
aws apigateway create-rest-api --name "det-status-api"
# Follow console steps or use Terraform

# 4. Get API URL
echo "API URL: https://XXXXX.execute-api.REGION.amazonaws.com/prod"
```

---

## Step 2: Deploy Validation Notifier (3 mins)

```bash
cd ../validation_notifier
zip function.zip handler.py

aws lambda create-function \
  --function-name det-validation-notifier \
  --runtime python3.12 \
  --role YOUR_LAMBDA_ROLE_ARN \
  --handler handler.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --environment Variables="{SLACK_BOT_TOKEN=xoxb-YOUR-TOKEN}" \
  --layers YOUR_SHARED_LAYER_ARN

# Note the Lambda ARN
```

---

## Step 3: Update Step Functions (2 mins)

Add to state machine after `TrackValidationSuccess`:

```json
"SendValidationNotification": {
  "Type": "Task",
  "Resource": "YOUR_VALIDATION_NOTIFIER_ARN",
  "Parameters": {
    "execution_id.$": "$$.Execution.Name",
    "service_request_id.$": "$.tracking_result.service_request_id",
    "slack_channel.$": "$.slack_channel",
    "slack_user.$": "$.slack_user",
    "project_name.$": "$.intake.project_name"
  },
  "ResultPath": "$.validation_notification",
  "Next": "CheckValidation",
  "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "CheckValidation"}]
}
```

---

## Step 4: Configure Slack Command (2 mins)

1. Go to https://api.slack.com/apps/YOUR_APP
2. Click "Slash Commands"
3. Click "Create New Command"
4. Fill in:
   - Command: `/aws-det-onboard-status`
   - Request URL: YOUR_BOT_URL
   - Description: Check onboarding request status

---

## Step 5: Start Slack Bot (3 mins)

```bash
cd ../

# Install dependencies
pip install requests slack-sdk slack-bolt

# Set environment variables
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_APP_TOKEN="xapp-your-token"
export STATUS_API_URL="https://XXXXX.execute-api.REGION.amazonaws.com/prod"

# Run bot
python main_with_api_gateway.py
```

---

## ✅ Verify It Works

### Test 1: Check Bot Started
```
INFO:slack_bolt.App:Starting to receive messages
```

### Test 2: Submit Request
In Slack:
```
/aws-det-poc
```
Fill form and submit.

### Test 3: Check Immediate Notification
You should receive a message within 5 seconds:
```
✅ Your Onboarding Request is Being Processed
🎫 Service Request ID: SR-20260608-1234
```

### Test 4: Check Status
```
/aws-det-onboard-status SR-20260608-1234
```

Should show formatted status with all steps.

### Test 5: Check Completion
Wait 30-45 seconds for completion notification with SR ID.

---

## 🎯 That's It!

All three features are now live:

✅ Service Request IDs  
✅ Immediate notifications  
✅ Status lookup command

---

## 📊 Monitor

```bash
# Watch Lambda logs
aws logs tail /aws/lambda/det-status-lookup --follow
aws logs tail /aws/lambda/det-validation-notifier --follow

# Check DynamoDB
aws dynamodb scan --table-name det-onboarding-prod-executions \
  --projection-expression "service_request_id,project_name,#status" \
  --expression-attribute-names '{"#status":"status"}' \
  --limit 5
```

---

## 🐛 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot won't start | Check `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` |
| Status command fails | Verify `STATUS_API_URL` is set |
| API returns 403 | Check Lambda permissions for API Gateway |
| No immediate notification | Check validation notifier Lambda logs |

---

## 📚 Full Documentation

- **Complete Guide:** `UPDATED_DEPLOYMENT.md`
- **Architecture Details:** `FINAL_SUMMARY.md`
- **Troubleshooting:** `IMPLEMENTATION_README.md`

---

**You're all set!** 🚀
