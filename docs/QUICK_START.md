# Quick Start Guide

Get the AWS DET Onboarding Bot running in 10 minutes.

---

## Prerequisites

Before starting, ensure you have:

- ✅ AWS account with admin or appropriate IAM permissions
- ✅ AWS CLI installed and configured
- ✅ Terraform 1.5+ installed
- ✅ GitHub Personal Access Token (with `repo` scope)
- ✅ HCP Terraform Token (organization access)
- ✅ Slack Bot Token and App Token
- ✅ Python 3.12+ (for local Slack bot)

---

## Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd onboard-aws-slack-bot-ai
```

---

## Step 2: Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# AWS Configuration
aws_region = "us-east-1"
environment = "prod"
project_name = "det-onboarding"

# GitHub Configuration
github_token = "ghp_xxxxxxxxxxxx"
github_owner = "your-org"

# HCP Terraform Configuration
hcp_terraform_token = "xxxxxxxxxxxx"
hcp_terraform_org = "your-org"
hcp_terraform_vcs_oauth_token_id = "ot-xxxxxxxxxxxx"

# Slack Configuration (for Lambda notifications)
slack_bot_token = "xoxb-xxxxxxxxxxxx"

# Optional: Allowed Slack channels (comma-separated)
det_allowed_channels = "C123456,C789012"
```

---

## Step 3: Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review what will be created
terraform plan

# Deploy (takes ~5 minutes)
terraform apply
```

Type `yes` when prompted.

**What gets created:**
- API Gateway (REST API endpoint)
- Step Functions state machine
- 8 Lambda functions
- Lambda shared layer
- DynamoDB tables (executions + logs)
- CloudWatch log groups
- IAM roles and policies

---

## Step 4: Get API Endpoint

```bash
# Save this URL - you'll need it for the Slack bot
terraform output api_gateway_url
```

Example output:
```
https://abc123def.execute-api.us-east-1.amazonaws.com/prod/onboard
```

---

## Step 5: Configure Slack Bot

```bash
cd ../src
```

Create or update `.env` file:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_APP_TOKEN=xapp-xxxxxxxxxxxx

# API Gateway Endpoint (from Step 4)
API_GATEWAY_ENDPOINT=https://abc123def.execute-api.us-east-1.amazonaws.com/prod/onboard

# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_OWNER=your-org

# HCP Terraform Configuration
HCP_TERRAFORM_TOKEN=xxxxxxxxxxxx
HCP_TERRAFORM_ORG=your-org

# Optional: Allowed channels
DET_ALLOWED_CHANNELS=["C123456","C789012"]
```

---

## Step 6: Start Slack Bot

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Start the bot
python main_with_api_gateway.py
```

You should see:
```
⚡️ Bolt app is running!
```

---

## Step 7: Test in Slack

### Test Form-Based Flow

1. Go to any allowed Slack channel
2. Type: `/aws-det-poc`
3. Fill the form that appears
4. Click **Submit**
5. See message: "Onboarding workflow started! Execution ID: `abc123-def456`"

### Test Chat-Based Flow

1. Go to any allowed Slack channel
2. Type: `/aws-det-onboard Create a Dev project called TestAPI`
3. Chat with the bot to provide details
4. Review the summary
5. Click **Approve** to start

---

## Step 8: Monitor Execution

### Via AWS Console

**Step Functions:**
```
AWS Console → Step Functions → State machines → det-onboarding-prod-onboarding-v2
```

**Lambda Logs:**
```
AWS Console → CloudWatch → Log groups → /aws/lambda/det-onboarding-prod-*
```

### Via AWS CLI

```bash
# Watch Step Functions logs
aws logs tail /aws/states/det-onboarding-prod-onboarding --follow

# Watch specific Lambda function
aws logs tail /aws/lambda/det-onboarding-prod-validate-intake --follow

# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn $(terraform output -raw state_machine_arn) \
  --max-results 10
```

### Via DynamoDB

```bash
# Query execution status
aws dynamodb get-item \
  --table-name det-onboarding-prod-executions \
  --key '{"execution_id": {"S": "abc123-def456"}}'
```

---

## What Happens Next?

After submission, the system automatically:

1. ✅ **Validates intake data** (2-5 seconds)
2. ✅ **Creates GitHub branch** (3-5 seconds)
3. ✅ **Commits intake document** (2-5 seconds)
4. ✅ **Creates HCP Terraform project** (3-5 seconds)
5. ✅ **Creates workspaces** (10-15 seconds, parallel)
6. ✅ **Configures variables** (5-10 seconds, parallel)
7. ✅ **Sends completion notification** to Slack

**Total time: ~30-45 seconds**

---

## Troubleshooting

### Issue: `terraform apply` fails

**Possible causes:**
- AWS credentials not configured
- Insufficient IAM permissions
- Invalid token values in terraform.tfvars

**Fix:**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Verify Terraform configuration
terraform validate

# Check for detailed errors
terraform apply -verbose
```

### Issue: API Gateway returns 502

**Possible causes:**
- Lambda function execution failure
- Missing environment variables
- Incorrect IAM permissions

**Fix:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/det-onboarding-prod-validate-intake --follow

# Verify environment variables
aws lambda get-function-configuration \
  --function-name det-onboarding-prod-validate-intake \
  --query 'Environment.Variables'
```

### Issue: Slack bot not responding

**Possible causes:**
- Bot not running
- Incorrect tokens in .env
- Socket mode not enabled

**Fix:**
```bash
# Verify bot is running
ps aux | grep python | grep main_with_api_gateway

# Check bot logs in terminal

# Verify Slack tokens
echo $SLACK_BOT_TOKEN
echo $SLACK_APP_TOKEN
```

### Issue: Step Functions execution fails

**Possible causes:**
- Invalid GitHub/HCP tokens
- Network connectivity issues
- API rate limits

**Fix:**
```bash
# Check execution error details
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>

# Check specific Lambda logs
aws logs tail /aws/lambda/det-onboarding-prod-<function-name> --follow

# Verify tokens in Lambda environment
aws lambda get-function-configuration \
  --function-name det-onboarding-prod-hcp-project
```

---

## Cost Estimation

### Monthly Costs (1000 requests/month)

| Service | Usage | Cost |
|---------|-------|------|
| API Gateway | 1,000 requests | $0.04 |
| Step Functions | 1,000 executions, 6 transitions each | $0.15 |
| Lambda | 8 functions × 1,000 invocations × 1 sec avg | $1.80 |
| DynamoDB | On-demand reads/writes | $0.25 |
| **Total** | | **~$2.24/month** |

**Note:** Costs scale with usage. CloudWatch Logs may add ~$0.50-1.00/month.

---

## Next Steps

1. ✅ **Test with Real Data** - Create an actual project
2. ✅ **Set Up Monitoring** - Configure CloudWatch alarms
3. ✅ **Enable Authentication** - Add API Gateway authorization for production
4. ✅ **Configure Notifications** - Set up SNS for failure alerts
5. ✅ **Review Security** - Audit IAM roles and token permissions

---

## Clean Up (Optional)

To remove all infrastructure:

```bash
cd terraform
terraform destroy
```

Type `yes` when prompted.

**Warning:** This will delete:
- All Lambda functions
- API Gateway
- Step Functions state machine
- DynamoDB tables (and all execution history)
- CloudWatch log groups (and all logs)

---

## Additional Resources

- [USER_JOURNEY.md](USER_JOURNEY.md) - Complete user workflow
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture details
- [AI_ORCHESTRATION.md](AI_ORCHESTRATION.md) - Chat interface guide

---

## Support

For issues:
1. Check CloudWatch Logs first
2. Review Step Functions execution graph
3. Verify DynamoDB execution records
4. Check Terraform state for resource configuration

---

**You're all set! The system is ready to automate your infrastructure onboarding. 🚀**
