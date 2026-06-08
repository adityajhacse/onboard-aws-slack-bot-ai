# Deployment Checklist

Quick checklist for deploying the enhanced status tracking features.

---

## ☑️ Pre-Deployment Checklist

- [ ] Review all code changes in `src/` folder
- [ ] Ensure `SLACK_BOT_TOKEN` is set in environment
- [ ] Ensure `DYNAMODB_TABLE` environment variable is configured
- [ ] Review `IMPLEMENTATION_README.md` for details
- [ ] Backup existing DynamoDB table (optional but recommended)

---

## 🚀 Deployment Steps

### Step 1: Update Shared Lambda Layer (DynamoDB Helper)

The shared layer with the updated `dynamodb_helper.py` is already in place at:
```
terraform/modules/lambda/lambda_functions/shared_layer/python/dynamodb_helper.py
```

**No action needed** - existing Lambdas will use the updated helper on next deployment.

---

### Step 2: Update Existing Lambda Functions

These Lambda functions reference the shared layer and will automatically get the updates:

```bash
cd terraform/modules/lambda/lambda_functions

# Status Tracker - already updated
# terraform/modules/lambda/lambda_functions/status_tracker/handler.py

# Completion Notifier - already updated
# terraform/modules/lambda/lambda_functions/completion_notifier/handler.py
```

**If using Terraform:**
```bash
cd terraform
terraform plan
terraform apply
```

**If deploying manually:**
```bash
# Re-package and deploy each function
cd terraform/modules/lambda/lambda_functions/status_tracker
zip -r function.zip handler.py
aws lambda update-function-code \
  --function-name det-onboarding-prod-status-tracker \
  --zip-file fileb://function.zip

cd ../completion_notifier
zip -r function.zip handler.py
aws lambda update-function-code \
  --function-name det-onboarding-prod-completion-notifier \
  --zip-file fileb://function.zip
```

---

### Step 3: Deploy Validation Notifier Lambda (NEW)

This is a NEW Lambda function that needs to be created:

```bash
cd src/validation_notifier
zip function.zip handler.py

# Create the Lambda function
aws lambda create-function \
  --function-name det-onboarding-prod-validation-notifier \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/YOUR_LAMBDA_ROLE \
  --handler handler.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables="{SLACK_BOT_TOKEN=YOUR_BOT_TOKEN}" \
  --layers arn:aws:lambda:REGION:ACCOUNT:layer:shared-layer:VERSION
```

**Replace:**
- `YOUR_ACCOUNT` - Your AWS account ID
- `YOUR_LAMBDA_ROLE` - ARN of your Lambda execution role
- `YOUR_BOT_TOKEN` - Your Slack bot token
- `REGION` - Your AWS region (e.g., us-east-1)
- `VERSION` - Version of your shared layer

**Note the ARN** of the created function for Step 4.

---

### Step 4: Update Step Functions State Machine

Add the validation notification step to your state machine.

**Location:** `terraform/modules/step_functions/state_machine.json.tpl`

**Insert this AFTER `TrackValidationSuccess`:**

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

**Also add the variable to the template:**

In `terraform/modules/step_functions/main.tf`:
```hcl
definition = templatefile("${path.module}/state_machine.json.tpl", {
  status_tracker_arn       = var.status_tracker_arn
  validation_notifier_arn  = var.validation_notifier_arn  # ADD THIS
  validate_intake_arn      = var.validate_intake_arn
  # ... rest of variables
})
```

**Then deploy:**
```bash
cd terraform
terraform plan
terraform apply
```

---

### Step 5: Register Slack Slash Command

1. Go to https://api.slack.com/apps
2. Select your app
3. Click "Slash Commands" in the sidebar
4. Click "Create New Command"
5. Fill in:
   - **Command:** `/aws-det-onboard-status`
   - **Request URL:** Your bot's URL (same as existing commands)
   - **Short Description:** Check the status of your onboarding request
   - **Usage Hint:** [SR-20260608-0042]
6. Click "Save"

---

### Step 6: Deploy Updated Slack Bot

The bot code in `src/main_with_api_gateway.py` has been updated with:
- New `/aws-det-onboard-status` command handler
- Status lookup functions
- DM-based SR ID recognition

**Restart the bot:**

```bash
cd src

# Install dependencies if needed
pip install boto3 slack-sdk slack-bolt

# Set environment variables
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_APP_TOKEN="xapp-your-token"
export DYNAMODB_TABLE="det-onboarding-prod-executions"
export AWS_REGION="us-east-1"

# Run the bot
python main_with_api_gateway.py
```

**For production deployment:**
- Deploy to EC2, ECS, or Lambda
- Ensure environment variables are set
- Enable auto-restart on failure

---

### Step 7: (Optional) Add DynamoDB GSI

For faster status lookups, add a Global Secondary Index:

**File:** `terraform/modules/dynamodb/main.tf`

```hcl
# Add this attribute
attribute {
  name = "service_request_id"
  type = "S"
}

# Add this GSI
global_secondary_index {
  name            = "service-request-id-index"
  hash_key        = "service_request_id"
  projection_type = "ALL"
}
```

**Deploy:**
```bash
cd terraform
terraform plan
terraform apply
```

**Note:** The code works WITHOUT the GSI (falls back to scan), but GSI is much faster for large tables.

---

## ✅ Post-Deployment Verification

### Test 1: Check Lambda Functions Exist

```bash
# Status Tracker (should already exist)
aws lambda get-function --function-name det-onboarding-prod-status-tracker

# Completion Notifier (should already exist)
aws lambda get-function --function-name det-onboarding-prod-completion-notifier

# Validation Notifier (NEW)
aws lambda get-function --function-name det-onboarding-prod-validation-notifier
```

### Test 2: Verify Step Functions Updated

```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:det-onboarding-prod-onboarding \
  --query 'definition' \
  --output text | jq . | grep -A5 "SendValidationNotification"
```

Should show the new validation notification step.

### Test 3: Test Service Request ID Generation

Submit a test onboarding request and check DynamoDB:

```bash
# Get the latest execution
aws dynamodb scan \
  --table-name det-onboarding-prod-executions \
  --limit 1 \
  --scan-index-forward false \
  --projection-expression "execution_id,service_request_id,project_name"
```

Should show `service_request_id` field with format like `SR-20260608-1234`.

### Test 4: Test Immediate Notification

1. Submit an onboarding request via Slack
2. Verify you receive TWO messages:
   - **First:** Validation passed notification (within 5 seconds)
   - **Second:** Completion notification (after 30-45 seconds)

### Test 5: Test Status Command

In Slack:
```
/aws-det-onboard-status SR-20260608-1234
```

Should display formatted status message.

### Test 6: Test DM Status Lookup

1. Open DM with the bot
2. Send a Service Request ID: `SR-20260608-1234`
3. Should receive status message immediately

### Test 7: Test Invalid SR ID

```
/aws-det-onboard-status SR-INVALID-9999
```

Should show "not found" message with helpful tips.

---

## 🔍 Monitoring Commands

### Check CloudWatch Logs

```bash
# Validation Notifier logs
aws logs tail /aws/lambda/det-onboarding-prod-validation-notifier --follow

# Status Tracker logs
aws logs tail /aws/lambda/det-onboarding-prod-status-tracker --follow

# Step Functions execution logs
aws logs tail /aws/states/det-onboarding-prod-onboarding --follow
```

### Query Recent Executions

```bash
# Get recent executions with SR IDs
aws dynamodb scan \
  --table-name det-onboarding-prod-executions \
  --filter-expression "attribute_exists(service_request_id)" \
  --projection-expression "execution_id,service_request_id,project_name,#status,created_at" \
  --expression-attribute-names '{"#status":"status"}' \
  --limit 10
```

### Check Slack Command Usage

In your bot logs:
```bash
grep "aws-det-onboard-status" bot.log | wc -l
```

---

## 🚨 Rollback Plan

If issues occur:

### 1. Rollback Slack Bot
```bash
git checkout HEAD~1 src/main_with_api_gateway.py
python src/main_with_api_gateway.py
```

### 2. Remove Validation Notifier Step
```bash
cd terraform
# Edit state_machine.json.tpl to remove SendValidationNotification step
terraform apply
```

### 3. Delete Validation Notifier Lambda (if needed)
```bash
aws lambda delete-function --function-name det-onboarding-prod-validation-notifier
```

### 4. Unregister Slash Command
- Go to Slack App settings
- Delete `/aws-det-onboard-status` command

---

## 📊 Success Metrics

After deployment, track:

- [ ] Service Request IDs being generated (check DynamoDB)
- [ ] Immediate notifications being sent (check CloudWatch)
- [ ] Status commands being used (check bot logs)
- [ ] No errors in Lambda logs
- [ ] Step Functions executions completing successfully

---

## 📞 Support

If you encounter issues:

1. Check CloudWatch logs for errors
2. Review `IMPLEMENTATION_README.md` for troubleshooting
3. Verify environment variables are set correctly
4. Ensure IAM permissions are correct

---

**Deployment completed!** 🎉

All features are now live:
- ✅ Service Request IDs
- ✅ Immediate notifications
- ✅ Status lookup command
