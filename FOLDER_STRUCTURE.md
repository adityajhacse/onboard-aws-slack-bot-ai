# Folder Structure

## Overview

This repository contains **two separate components**:

1. **Slack Bot** (runs on your server) → `src/`
2. **AWS Infrastructure** (deployed to AWS) → `terraform/`

---

## 📁 src/ - Slack Bot (Server-Side)

**What it is:** Python application that runs on your server and connects to Slack

**What's inside:**
- `main_with_api_gateway.py` - Main Slack bot application
- `status_api_client.py` - HTTP client to call AWS API Gateway
- `api_gateway_client.py` - Client for onboarding API
- `ai_orchestrator.py` - AI chat orchestration
- `modal_lib.py` - Slack modal builders
- `github_api.py` - GitHub API helpers
- `requirements.txt` - Python dependencies

**Dependencies:**
- slack-sdk
- slack-bolt
- requests
- certifi

**How to run:**
```bash
cd src
pip install -r requirements.txt
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
export STATUS_API_URL="https://your-api-url/status"
python3 main_with_api_gateway.py
```

**Key Point:** This does NOT use boto3 or AWS SDK. It only makes HTTP requests to API Gateway.

---

## 📁 terraform/ - AWS Infrastructure

**What it is:** Terraform configuration that deploys AWS resources

**What's inside:**

### Lambda Functions (`terraform/modules/lambda/lambda_functions/`)

All Lambda functions that run **in AWS**:

1. **validate_intake/** - Validate intake data
2. **github_branch/** - Create GitHub branch
3. **github_commit/** - Commit to GitHub
4. **hcp_project/** - Create HCP Terraform project
5. **hcp_workspace/** - Create workspaces
6. **hcp_vars/** - Configure workspace variables
7. **status_tracker/** - Track execution status
8. **completion_notifier/** - Send completion notifications
9. **status_lookup/** - ✨ API endpoint for status queries
10. **validation_notifier/** - ✨ Immediate validation notifications
11. **shared_layer/python/** - Shared utilities (dynamodb_helper.py, etc.)

### Infrastructure Modules

- **api_gateway/** - API Gateway REST API
- **step_functions/** - Step Functions state machine
- **dynamodb/** - DynamoDB tables
- **iam/** - IAM roles and policies

**How to deploy:**
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

---

## ✅ Correct Locations

| Component | Location | Runs On |
|-----------|----------|---------|
| Slack Bot | `src/` | Your server |
| status_lookup Lambda | `terraform/modules/lambda/lambda_functions/status_lookup/` | AWS Lambda |
| validation_notifier Lambda | `terraform/modules/lambda/lambda_functions/validation_notifier/` | AWS Lambda |
| status_api_client | `src/status_api_client.py` | Your server (Slack bot) |
| dynamodb_helper | `terraform/modules/lambda/lambda_functions/shared_layer/python/` | AWS Lambda Layer |

---

## ❌ Common Mistakes

### Wrong: Lambda functions in src/
```
src/
├── status_lookup_lambda/     ❌ WRONG - This is AWS Lambda
├── validation_notifier/      ❌ WRONG - This is AWS Lambda
```

These should be in `terraform/modules/lambda/lambda_functions/` instead!

### Wrong: boto3 in Slack bot
```python
# src/main.py
import boto3  ❌ WRONG - Slack bot should use HTTP, not boto3
```

The Slack bot should use `requests` to call API Gateway, not boto3 directly.

---

## 🔄 Data Flow

```
User (Slack)
    ↓
Slack Bot (src/main_with_api_gateway.py)
    ↓ HTTP GET
API Gateway
    ↓
status_lookup Lambda (terraform/.../status_lookup/)
    ↓
DynamoDB
```

**Key Points:**
- Slack Bot → HTTP → API Gateway
- Lambda functions → boto3 → DynamoDB
- No direct boto3 usage in Slack bot

---

## 📦 Dependencies

### Slack Bot (`src/requirements.txt`)
```
slack-sdk>=3.19.0
slack-bolt>=1.16.0
requests>=2.31.0
certifi>=2023.0.0
```

### Lambda Functions (via shared layer)
```
boto3 (pre-installed in Lambda)
requests
certifi
```

---

## 🚀 Deployment Process

### 1. Deploy AWS Infrastructure First
```bash
cd terraform
terraform apply
```

This creates:
- All Lambda functions
- API Gateway endpoints
- DynamoDB tables
- Step Functions

### 2. Get API URL
```bash
terraform output status_api_url
```

### 3. Configure Slack Bot
```bash
export STATUS_API_URL=$(terraform output -raw status_api_url)
```

### 4. Run Slack Bot
```bash
cd src
python3 main_with_api_gateway.py
```

---

## 📝 Summary

**Two separate deployments:**
1. **AWS Infrastructure** (Terraform) - Lambda functions, API Gateway, DynamoDB
2. **Slack Bot** (Python app) - Runs on your server, calls AWS APIs

**Clear separation:**
- ✅ Lambda code lives in `terraform/`
- ✅ Slack bot code lives in `src/`
- ✅ No mixing of the two

This keeps everything organized and maintainable! 🎯
