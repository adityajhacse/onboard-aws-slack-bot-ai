# Terraform Setup Instructions

## Quick Start

1. **Edit `terraform.tfvars`** with your actual credentials
2. Run `terraform init`
3. Run `terraform plan` to review
4. Run `terraform apply` to deploy

## Required Variables to Fill In

### 🔑 GitHub Configuration

```bash
# Get your GitHub token
# Visit: https://github.com/settings/tokens
# Click: Generate new token (classic)
# Select scopes: repo (full control)
# Copy the token and paste below

github_token       = "ghp_your_token_here"
github_owner       = "your-github-username-or-org"
github_repo        = "your-terraform-repo-name"
```

**Example:**
```hcl
github_token       = "ghp_ABC123XYZ456..."
github_owner       = "mycompany"
github_repo        = "terraform-infrastructure"
```

---

### 🔑 HCP Terraform Configuration

```bash
# Get your HCP Terraform token
# Visit: https://app.terraform.io/app/settings/tokens
# Click: Create an API token
# Copy and paste below

hcp_terraform_token = "your_hcp_token_here"
hcp_terraform_org   = "your-hcp-org-name"
```

**Get OAuth Token ID:**
```bash
# Run this to get your VCS OAuth token ID
cd ../
python3 src/get_hcp_vcs_oauth_token_id.py --org your-org-name

# Copy the token ID (format: ot-xxxxxxxxxxxxx)
```

**Example:**
```hcl
hcp_terraform_token              = "AtlasV1.abc123..."
hcp_terraform_org                = "my-company"
hcp_terraform_vcs_oauth_token_id = "ot-xyz789abc123"
```

---

### 🔑 Slack Configuration

```bash
# Get your Slack bot token
# Visit: https://api.slack.com/apps
# Select your app
# Go to: OAuth & Permissions
# Copy: Bot User OAuth Token (starts with xoxb-)

slack_bot_token = "xoxb-your-token-here"
```

**Example:**
```hcl
slack_bot_token = "xoxb-123456789012-1234567890123-ABC123XYZ456..."
```

---

### 🔑 AWS IAM Role

Update with your AWS account ID:

```hcl
hcp_tfc_aws_run_role_arn = "arn:aws:iam::YOUR_ACCOUNT_ID:role/HCP-terraform-role"
```

**Find your AWS Account ID:**
```bash
aws sts get-caller-identity --query Account --output text
```

**Example:**
```hcl
hcp_tfc_aws_run_role_arn = "arn:aws:iam::123456789012:role/HCP-terraform-role"
```

---

## Using Environment Variables (Alternative)

Instead of putting sensitive values in `terraform.tfvars`, you can use environment variables:

```bash
# Set environment variables (recommended for security)
export TF_VAR_github_token="ghp_..."
export TF_VAR_hcp_terraform_token="..."
export TF_VAR_slack_bot_token="xoxb-..."

# Then just run terraform commands
terraform plan
terraform apply
```

---

## Using AWS Secrets Manager (Production)

For production, store secrets in AWS Secrets Manager:

```bash
# Store secrets
aws secretsmanager create-secret \
  --name det-onboarding/github-token \
  --secret-string "ghp_..."

aws secretsmanager create-secret \
  --name det-onboarding/hcp-terraform-token \
  --secret-string "..."

aws secretsmanager create-secret \
  --name det-onboarding/slack-bot-token \
  --secret-string "xoxb-..."
```

Then update Lambda functions to read from Secrets Manager.

---

## Minimal terraform.tfvars Example

Here's a complete example with fake values (replace with real ones):

```hcl
# AWS Configuration
aws_region  = "us-east-1"
environment = "prod"
project_name = "det-onboarding"

# GitHub Configuration
github_token       = "ghp_ABC123XYZ456DEF789GHI012JKL345MNO678"
github_owner       = "mycompany"
github_repo        = "terraform-config"
github_base_branch = "main"

# HCP Terraform Configuration
hcp_terraform_token              = "AtlasV1.abcdefghijklmnopqrstuvwxyz123456789"
hcp_terraform_org                = "mycompany"
hcp_terraform_url                = "https://app.terraform.io"
hcp_terraform_vcs_oauth_token_id = "ot-xyz789abc123def456"
hcp_terraform_github_app_installation_id = ""
hcp_tfc_aws_run_role_arn         = "arn:aws:iam::123456789012:role/HCP-terraform-role"

# Slack Configuration
slack_bot_token = ""

# Lambda Configuration
lambda_runtime     = "python3.12"
lambda_memory_size = 512
lambda_timeout     = 60

# Tags
tags = {
  ManagedBy   = "Terraform"
  Project     = "DET-Onboarding"
  Environment = "prod"
  Team        = "Platform"
}
```

---

## Deployment Steps

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

Expected output:
```
Initializing the backend...
Initializing provider plugins...
Terraform has been successfully initialized!
```

### 2. Validate Configuration

```bash
terraform validate
```

Expected output:
```
Success! The configuration is valid.
```

### 3. Plan Deployment

```bash
terraform plan
```

Review the output. You should see:
- 2 DynamoDB tables
- 8 Lambda functions
- 1 Lambda layer
- 1 Step Functions state machine
- 1 API Gateway
- Multiple IAM roles and policies
- CloudWatch log groups

### 4. Apply Configuration

```bash
terraform apply
```

Type `yes` when prompted.

Deployment takes approximately 3-5 minutes.

### 5. Capture Outputs

```bash
terraform output
```

Save these values:
- `api_gateway_url` - Use in Slack app
- `state_machine_arn` - For monitoring
- `dynamodb_table_name` - For queries

---

## Troubleshooting

### Error: Invalid credentials

**Problem:** Terraform can't authenticate to AWS
**Solution:**
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and Region
```

### Error: github_token is required

**Problem:** terraform.tfvars not found or empty
**Solution:**
```bash
# Make sure you're in the terraform directory
cd terraform
ls -la terraform.tfvars

# If file is missing, copy from example
cp terraform.tfvars.example terraform.tfvars
# Then edit with your values
```

### Error: Invalid HCP Terraform token

**Problem:** Token is expired or incorrect
**Solution:**
1. Go to https://app.terraform.io/app/settings/tokens
2. Create a new API token
3. Update `hcp_terraform_token` in terraform.tfvars

### Error: Slack bot token invalid

**Problem:** Token is incorrect or bot is not installed
**Solution:**
1. Go to https://api.slack.com/apps
2. Select your app
3. Go to OAuth & Permissions
4. Copy Bot User OAuth Token
5. Make sure bot is installed in your workspace

---

## Security Checklist

- [ ] `terraform.tfvars` is in `.gitignore`
- [ ] File permissions set to 600: `chmod 600 terraform.tfvars`
- [ ] Tokens have minimum required scopes
- [ ] AWS IAM roles follow least-privilege principle
- [ ] Consider using AWS Secrets Manager for production
- [ ] Enable CloudTrail for audit logging
- [ ] Enable MFA for AWS account

---

## Next Steps After Deployment

1. **Test the API endpoint:**
   ```bash
   curl -X POST $(terraform output -raw api_gateway_url) \
     -H "Content-Type: application/json" \
     -d @../test_payload.json
   ```

2. **Update Slack app:**
   ```bash
   export API_GATEWAY_ENDPOINT=$(terraform output -raw api_gateway_url)
   cd ../src
   python main_with_api_gateway.py
   ```

3. **Test via Slack:**
   - Run `/aws-det-poc` in Slack
   - Fill out the form
   - Submit and verify execution

4. **Monitor execution:**
   ```bash
   # View Step Functions logs
   aws logs tail /aws/states/det-onboarding-prod-onboarding --follow
   
   # Check DynamoDB
   aws dynamodb scan --table-name det-onboarding-prod-executions --limit 5
   ```

---

## Cost Monitoring

After deployment, monitor costs:

```bash
# View cost for last 30 days
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '30 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter file://filter.json
```

Expected monthly cost: **~$5.63 for 1,000 executions**

---

## Support

- **Documentation**: See README.md files in project root
- **Issues**: Check CloudWatch Logs for error details
- **AWS Console**: 
  - Step Functions: https://console.aws.amazon.com/states
  - Lambda: https://console.aws.amazon.com/lambda
  - DynamoDB: https://console.aws.amazon.com/dynamodb
