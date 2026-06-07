# Token Storage Guide

## Where Tokens Are Stored

### 📋 Summary

| Token | Storage Location | Access Method | Security Level |
|-------|-----------------|---------------|----------------|
| GitHub Token | `terraform.tfvars` → Lambda env vars | Lambda reads `GITHUB_TOKEN` | ⚠️ Basic |
| HCP Terraform Token | `terraform.tfvars` → Lambda env vars | Lambda reads `HCP_TERRAFORM_TOKEN` | ⚠️ Basic |
| Slack Bot Token | `terraform.tfvars` → Lambda env vars | Lambda reads `SLACK_BOT_TOKEN` | ⚠️ Basic |
| AWS Credentials | AWS IAM Roles (no storage needed) | Lambda execution role | ✅ Secure |

---

## Current Implementation (Basic Security)

### 1. **terraform.tfvars** (Local Development)

```hcl
# File: terraform/terraform.tfvars
github_token        = "ghp_your_token_here"
hcp_terraform_token = "your_hcp_token"
slack_bot_token     = "xoxb-your_slack_token"
```

**Security:**
- File permissions: `600` (owner read/write only)
- Added to `.gitignore` (NOT committed to Git)
- Used only during `terraform apply`

### 2. **Terraform → Lambda Environment Variables**

Terraform passes tokens to Lambda functions as environment variables:

```hcl
# File: terraform/main.tf
locals {
  common_env_vars = {
    GITHUB_TOKEN                   = var.github_token
    HCP_TERRAFORM_TOKEN            = var.hcp_terraform_token
    SLACK_BOT_TOKEN                = var.slack_bot_token
    # ... other config
  }
}

# Each Lambda function gets these environment variables
resource "aws_lambda_function" "github_commit" {
  environment {
    variables = local.common_env_vars  # ← Tokens passed here
  }
}
```

### 3. **Lambda Functions Read from Environment**

```python
# File: lambda_functions/github_commit/handler.py
import os

def lambda_handler(event, context):
    # Read token from environment variable
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    
    # Use token to call GitHub API
    result = github_api.commit_file(token=token, ...)
```

### 4. **AWS Encrypts Environment Variables**

- Lambda automatically encrypts environment variables at rest
- Uses AWS KMS (Key Management Service)
- Decrypted only when Lambda executes

---

## Token Flow

```
Developer Machine
    ↓
terraform.tfvars (plain text, chmod 600, .gitignored)
    ↓
terraform apply (loads variables)
    ↓
AWS Lambda Configuration (encrypted at rest with KMS)
    ↓
Lambda Execution (decrypted in memory)
    ↓
API calls to GitHub/HCP/Slack
```

---

## Security Levels

### ⚠️ Basic Security (Current Implementation)

**Pros:**
- ✅ Simple to set up
- ✅ No additional AWS services needed
- ✅ Tokens encrypted at rest by AWS
- ✅ Not in Git repository

**Cons:**
- ⚠️ Tokens visible in Lambda console (to authorized users)
- ⚠️ Tokens in Terraform state file (encrypted backend recommended)
- ⚠️ Rotation requires Terraform apply

**Good for:** Development, testing, small teams

---

### ✅ Production Security (Recommended Upgrade)

Use **AWS Secrets Manager** to store tokens:

#### Step 1: Store Secrets

```bash
# Store GitHub token
aws secretsmanager create-secret \
  --name det-onboarding/github-token \
  --description "GitHub API token for DET onboarding" \
  --secret-string "ghp_your_token_here"

# Store HCP Terraform token
aws secretsmanager create-secret \
  --name det-onboarding/hcp-terraform-token \
  --secret-string "your_hcp_token"

# Store Slack bot token
aws secretsmanager create-secret \
  --name det-onboarding/slack-bot-token \
  --secret-string "xoxb-your_slack_token"
```

#### Step 2: Update Terraform

```hcl
# File: terraform/variables.tf
variable "secrets_manager_enabled" {
  description = "Use AWS Secrets Manager for tokens"
  type        = bool
  default     = true
}

# File: terraform/main.tf
locals {
  common_env_vars = {
    # Pass secret ARNs instead of actual tokens
    GITHUB_TOKEN_SECRET_ARN        = var.secrets_manager_enabled ? aws_secretsmanager_secret.github_token.arn : ""
    HCP_TERRAFORM_TOKEN_SECRET_ARN = var.secrets_manager_enabled ? aws_secretsmanager_secret.hcp_token.arn : ""
    SLACK_BOT_TOKEN_SECRET_ARN     = var.secrets_manager_enabled ? aws_secretsmanager_secret.slack_token.arn : ""
    
    # For backward compatibility
    GITHUB_TOKEN        = var.secrets_manager_enabled ? "" : var.github_token
    HCP_TERRAFORM_TOKEN = var.secrets_manager_enabled ? "" : var.hcp_terraform_token
    SLACK_BOT_TOKEN     = var.secrets_manager_enabled ? "" : var.slack_bot_token
  }
}
```

#### Step 3: Update Lambda Code

```python
# File: lambda_functions/shared_layer/python/secrets_helper.py
import boto3
import json
from functools import lru_cache

secretsmanager = boto3.client('secretsmanager')

@lru_cache(maxsize=10)
def get_secret(secret_arn: str) -> str:
    """Get secret from AWS Secrets Manager with caching."""
    response = secretsmanager.get_secret_value(SecretId=secret_arn)
    return response['SecretString']

def get_github_token() -> str:
    """Get GitHub token from Secrets Manager or environment."""
    secret_arn = os.environ.get('GITHUB_TOKEN_SECRET_ARN')
    if secret_arn:
        return get_secret(secret_arn)
    return os.environ.get('GITHUB_TOKEN', '')

def get_hcp_token() -> str:
    """Get HCP Terraform token from Secrets Manager or environment."""
    secret_arn = os.environ.get('HCP_TERRAFORM_TOKEN_SECRET_ARN')
    if secret_arn:
        return get_secret(secret_arn)
    return os.environ.get('HCP_TERRAFORM_TOKEN', '')

def get_slack_token() -> str:
    """Get Slack bot token from Secrets Manager or environment."""
    secret_arn = os.environ.get('SLACK_BOT_TOKEN_SECRET_ARN')
    if secret_arn:
        return get_secret(secret_arn)
    return os.environ.get('SLACK_BOT_TOKEN', '')
```

#### Step 4: Update IAM Permissions

```hcl
# File: terraform/iam.tf
resource "aws_iam_role_policy" "lambda_secrets_manager" {
  name   = "${local.name_prefix}-lambda-secrets-manager"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_secrets_manager.json
}

data "aws_iam_policy_document" "lambda_secrets_manager" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      aws_secretsmanager_secret.github_token.arn,
      aws_secretsmanager_secret.hcp_token.arn,
      aws_secretsmanager_secret.slack_token.arn
    ]
  }
}
```

**Benefits:**
- ✅ Tokens never in Lambda console
- ✅ Centralized secret management
- ✅ Automatic rotation support
- ✅ Audit logging (who accessed when)
- ✅ Fine-grained access control
- ✅ No Terraform apply needed for rotation

**Cost:** ~$0.40/month per secret + $0.05 per 10,000 API calls

---

## Alternative: Environment Variables via CI/CD

For automated deployments, pass tokens from CI/CD secrets:

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Deploy Infrastructure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Deploy with Terraform
        env:
          TF_VAR_github_token: ${{ secrets.GITHUB_TOKEN }}
          TF_VAR_hcp_terraform_token: ${{ secrets.HCP_TERRAFORM_TOKEN }}
          TF_VAR_slack_bot_token: ${{ secrets.SLACK_BOT_TOKEN }}
        run: |
          cd terraform
          terraform init
          terraform apply -auto-approve
```

**Tokens stored in:**
- GitHub Secrets (encrypted, never in logs)
- Passed as environment variables to Terraform
- Never written to disk

---

## Token Rotation

### Current Implementation (Manual)

1. Generate new token in GitHub/HCP/Slack
2. Update `terraform.tfvars`
3. Run `terraform apply`
4. Lambda functions automatically use new token

### With Secrets Manager (Recommended)

```bash
# Rotate GitHub token
aws secretsmanager update-secret \
  --secret-id det-onboarding/github-token \
  --secret-string "ghp_new_token_here"

# Lambda functions automatically use new token (cached for 5 minutes)
```

---

## Security Best Practices

### ✅ DO

1. **Use AWS Secrets Manager for production**
2. **Enable Terraform state encryption:**
   ```hcl
   terraform {
     backend "s3" {
       bucket  = "terraform-state-bucket"
       key     = "det-onboarding/terraform.tfstate"
       encrypt = true  # ← Enable encryption
     }
   }
   ```
3. **Use IAM roles instead of access keys**
4. **Rotate tokens regularly** (every 90 days)
5. **Enable CloudTrail** to audit secret access
6. **Use least-privilege IAM policies**
7. **Set file permissions:** `chmod 600 terraform.tfvars`

### ❌ DON'T

1. **Never commit terraform.tfvars to Git**
2. **Never hardcode tokens in Lambda code**
3. **Never log token values**
4. **Never share tokens via email/chat**
5. **Never use root AWS credentials**

---

## Checking Where Tokens Are

### 1. Check terraform.tfvars (Local)

```bash
cat terraform/terraform.tfvars
# Shows plain text tokens (only on your machine)
```

### 2. Check Lambda Environment Variables (AWS Console)

```
AWS Console → Lambda → Function → Configuration → Environment variables
```

Shows: Encrypted values (visible to authorized users)

### 3. Check Terraform State (if using remote backend)

```bash
terraform state pull | grep -i token
# Shows tokens in state (should be encrypted backend)
```

### 4. Check Secrets Manager (if enabled)

```bash
aws secretsmanager list-secrets
aws secretsmanager get-secret-value --secret-id det-onboarding/github-token
```

---

## Migration Path to Secrets Manager

If you want to upgrade to Secrets Manager later:

1. **Phase 1** (Now): Use terraform.tfvars (current implementation)
2. **Phase 2**: Test in dev with Secrets Manager
3. **Phase 3**: Migrate production to Secrets Manager
4. **Phase 4**: Remove tokens from terraform.tfvars

No downtime needed - both methods can coexist during migration.

---

## Summary

**Current Storage:**
```
terraform.tfvars → Terraform variables → Lambda environment variables (KMS encrypted)
                                              ↓
                                    Lambda reads os.environ.get()
```

**Recommended Production:**
```
AWS Secrets Manager (encrypted, rotatable, audited)
                    ↓
            Lambda IAM role permissions
                    ↓
    Lambda calls secretsmanager.get_secret_value()
```

Both methods work - current is simpler, Secrets Manager is more secure for production.
