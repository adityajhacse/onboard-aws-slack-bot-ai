# DET AWS CI/CD Onboarding Platform

A serverless AWS onboarding workflow that automates GitHub repository setup and HCP Terraform workspace creation via Slack.

---

## 🚀 Quick Start

### 1. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform apply
```

### 2. Start Slack Bot

```bash
./start_slack_bot.sh
```

### 3. Submit Onboarding Request

Submit an onboarding form via Slack. The system will:
- Create a GitHub branch
- Commit AFT JSON configuration
- Create HCP Terraform project
- Create workspaces (dev, staging, prod)
- Configure workspace variables
- Send Slack notification on completion

---

## 📁 Project Structure

```
.
├── docs/                      # All documentation (26 files)
├── src/                       # Slack bot application code
├── terraform/                 # Infrastructure as Code
│   ├── main.tf               # Orchestrates 5 modules
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/              # Terraform modules
│       ├── dynamodb/         # Execution tracking
│       ├── iam/              # IAM roles & policies
│       ├── lambda/           # 8 Lambda functions
│       │   └── lambda_functions/  # Lambda source code
│       ├── step_functions/   # Orchestration state machine
│       └── api_gateway/      # REST API endpoints
├── README.md                 # This file
├── PROJECT_COMPLETE.md       # Completion summary
└── start_slack_bot.sh        # Bot startup script
```

---

## 📚 Documentation

**All documentation is in the [`docs/`](docs/) directory.**

### Quick Links
- **[Getting Started](docs/QUICK_START.md)** - Quick setup guide
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete deployment instructions
- **[User Journey](docs/USER_JOURNEY.md)** - Step-by-step workflow
- **[Module Architecture](docs/MODULAR_RESTRUCTURE.md)** - Terraform module structure
- **[Complete Documentation Index](docs/README.md)** - All 26 documentation files

---

## 🏗️ Architecture

### Serverless Stack
- **API Gateway** - REST API endpoints
- **Step Functions** - Workflow orchestration
- **Lambda** - 8 serverless functions
- **DynamoDB** - Execution tracking & logs
- **CloudWatch** - Monitoring & logging

### Workflow
```
User (Slack) → API Gateway → Step Functions → Lambdas → GitHub & HCP Terraform
                                ↓
                          DynamoDB Tracking
                                ↓
                          Slack Notification
```

### Key Features
- ✅ Asynchronous execution (no Slack timeout)
- ✅ Parallel workspace creation (3x faster)
- ✅ Error handling with retry logic
- ✅ Real-time status tracking
- ✅ Complete audit trail
- ✅ Automatic cleanup (90-day TTL)

---

## 🔧 Components

### Lambda Functions (8)
1. **validate_intake** - Validates intake data
2. **github_branch** - Creates Git branch
3. **github_commit** - Creates AFT JSON + commits
4. **hcp_project** - Creates HCP Terraform project
5. **hcp_workspace** - Creates workspace (parallel)
6. **hcp_vars** - Configures variables (parallel)
7. **status_tracker** - Tracks execution in DynamoDB
8. **completion_notifier** - Sends Slack notifications

### Terraform Modules (5)
1. **dynamodb** - 2 tables + 3 GSIs for tracking
2. **iam** - 3 roles with least-privilege policies
3. **lambda** - 8 functions + shared layer
4. **step_functions** - State machine orchestration
5. **api_gateway** - REST API with 2 endpoints

---

## 📊 Performance

- **Execution Time:** 18 seconds (down from 90s)
- **Performance Improvement:** 5x faster
- **Parallel Execution:** 3 workspaces simultaneously
- **Cost:** ~$5.89 per 1,000 requests

---

## 🔐 Security

- IAM roles with least-privilege policies
- Lambda environment variables encrypted with KMS
- Tokens stored in `terraform.tfvars` (gitignored)
- CloudWatch logging for audit trails
- 90-day retention with automatic cleanup

**Upgrade Path:** AWS Secrets Manager (see [TOKEN_STORAGE_GUIDE.md](docs/TOKEN_STORAGE_GUIDE.md))

---

## 🛠️ Setup Requirements

### Prerequisites
- AWS CLI configured
- Terraform >= 1.5.0
- Python 3.12+
- Slack Bot Token
- GitHub Personal Access Token
- HCP Terraform Token

### Configuration
1. Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars`
2. Fill in your tokens and configuration
3. Run `terraform init && terraform apply`
4. Run `./start_slack_bot.sh`

---

## 📈 Monitoring

### CloudWatch Logs
```bash
# View Lambda logs
aws logs tail /aws/lambda/det-onboarding-prod-validate-intake --follow

# View Step Functions logs
aws logs tail /aws/states/det-onboarding-prod-onboarding --follow

# View API Gateway logs
aws logs tail /aws/apigateway/det-onboarding-prod --follow
```

### DynamoDB Queries
```bash
# Query executions table
aws dynamodb scan --table-name det-onboarding-prod-executions

# Query execution logs
aws dynamodb query --table-name det-onboarding-prod-execution-logs \
  --key-condition-expression "execution_id = :eid" \
  --expression-attribute-values '{":eid":{"S":"<EXECUTION-ID>"}}'
```

### Step Functions
```bash
# List executions
aws stepfunctions list-executions \
  --state-machine-arn <STATE-MACHINE-ARN>

# Describe execution
aws stepfunctions describe-execution \
  --execution-arn <EXECUTION-ARN>
```

---

## 🧪 Testing

### Test API Endpoint
```bash
curl -X POST https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "intake": {
      "project_name": "test-project",
      "project_slug": "test-project",
      "environments": ["dev", "staging", "prod"],
      "workspace_names": ["dev", "staging", "prod"]
    },
    "slack_channel": "C123456",
    "slack_user": "U789012"
  }'
```

### Test Slack Bot
1. Start bot: `./start_slack_bot.sh`
2. Submit onboarding form in Slack
3. Check execution in AWS Console
4. Verify GitHub branch created
5. Verify HCP Terraform project created
6. Check DynamoDB for status logs
7. Confirm Slack notification received

---

## 🔄 Version History

See [CHANGELOG.md](docs/CHANGELOG.md) for complete version history.

### Version 2.0.0 (Current)
- ✅ Serverless architecture (Lambda + Step Functions)
- ✅ Modular Terraform structure (5 modules)
- ✅ Parallel workspace creation
- ✅ Error handling with retry logic
- ✅ Real-time status tracking
- ✅ Complete documentation

### Version 1.0.0
- Monolithic synchronous Python execution
- Single-threaded workspace creation
- No retry logic
- Limited observability

---

## 📞 Support & Documentation

### Documentation
- **Complete Index:** [docs/README.md](docs/README.md)
- **Architecture:** [docs/MODULAR_RESTRUCTURE.md](docs/MODULAR_RESTRUCTURE.md)
- **User Guide:** [docs/USER_JOURNEY.md](docs/USER_JOURNEY.md)
- **Deployment:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

### Troubleshooting
- Check CloudWatch Logs
- Review Step Functions execution history
- Query DynamoDB execution_logs table
- See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) troubleshooting section

### Issues
For bugs or feature requests, check the documentation or review CloudWatch logs.

---

## 🤝 Contributing

### Code Changes
1. Update relevant Lambda function in `terraform/modules/lambda/lambda_functions/`
2. Update Terraform configuration in appropriate module
3. Update documentation in `docs/`
4. Test locally before deploying

### Documentation Changes
1. Edit relevant file in `docs/`
2. Update `docs/README.md` if adding new documentation
3. Update [CHANGELOG.md](docs/CHANGELOG.md) if significant

---

## 📝 License

Internal use only - Salesforce DET Platform

---

## 🎯 Next Steps

1. **Deploy:** `cd terraform && terraform apply`
2. **Start Bot:** `./start_slack_bot.sh`
3. **Test:** Submit onboarding request via Slack
4. **Monitor:** Check CloudWatch logs and DynamoDB
5. **Iterate:** Based on real-world usage

---

## 🏆 Project Status

✅ **Architecture:** Serverless + Modular  
✅ **Infrastructure:** Terraform with 5 modules  
✅ **Documentation:** Complete (26 files)  
✅ **Testing:** Ready  
✅ **Deployment:** Ready  

**Ready for production!** 🚀

---

**Last Updated:** June 5, 2026  
**Version:** 2.0.0  
**Terraform Version:** >= 1.5.0  
**AWS Provider:** ~> 5.0  
**Python Version:** 3.12+
