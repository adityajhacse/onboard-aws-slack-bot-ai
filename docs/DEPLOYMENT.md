# Deployment Guide - Step Functions Architecture

This guide explains how to deploy and use the refactored Step Functions-based architecture.

## Overview

The project has been refactored from a monolithic synchronous process to a serverless architecture using:
- **AWS Lambda** for independent function execution
- **AWS Step Functions** for workflow orchestration with retry logic
- **API Gateway** for triggering workflows
- **DynamoDB** for execution tracking

## Architecture Changes

### Before (Monolithic)
```
Slack → Python App → (GitHub + HCP Terraform) → Response
```
All steps executed synchronously in one process. If any step failed, the entire process failed.

### After (Step Functions)
```
Slack → API Gateway → Step Functions → Multiple Lambda Functions → Response
```
Each step is independent with its own retry logic. Failures are isolated and can be retried independently.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Terraform** 1.5.0+
3. **AWS CLI** configured
4. **Python** 3.12+
5. **Slack App** configured
6. **GitHub Token** with repo access
7. **HCP Terraform Token**

## Deployment Steps

### Step 1: Prepare Infrastructure Code

All Terraform code is in the `terraform/` directory:

```bash
cd terraform
```

### Step 2: Configure Variables

Create `terraform.tfvars` from the example:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# AWS Configuration
aws_region  = "us-east-1"
environment = "prod"

# GitHub Configuration  
github_token       = "ghp_xxxxx"
github_owner       = "your-org"
github_repo        = "your-repo"
github_base_branch = "main"

# HCP Terraform Configuration
hcp_terraform_token                      = "xxxxx"
hcp_terraform_org                        = "your-org"
hcp_terraform_vcs_oauth_token_id         = "ot-xxxxx"
hcp_tfc_aws_run_role_arn                 = "arn:aws:iam::xxxx:role/HCP-terraform-role"

# Slack Configuration
slack_bot_token = "xoxb-xxxxx"
```

### Step 3: Initialize Terraform

```bash
terraform init
```

### Step 4: Review Planned Changes

```bash
terraform plan
```

Review the output to ensure:
- 6 Lambda functions will be created
- 1 Step Functions state machine
- 1 API Gateway
- 1 DynamoDB table
- IAM roles and policies

### Step 5: Deploy Infrastructure

```bash
terraform apply
```

Type `yes` when prompted.

Deployment takes approximately 3-5 minutes.

### Step 6: Capture API Gateway URL

After deployment completes:

```bash
terraform output api_gateway_url
```

Save this URL - you'll need it for the Slack app configuration.

Example output:
```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/onboard
```

### Step 7: Update Slack App

#### Option A: Use the New main_with_api_gateway.py

Replace the existing `main.py` or set an environment variable:

```bash
export API_GATEWAY_ENDPOINT="<api_gateway_url from step 6>"
```

Then run the modified Slack app:

```bash
cd ../src
python main_with_api_gateway.py
```

#### Option B: Keep Existing main.py (Synchronous)

Keep using the original `main.py` if you want to test before switching:

```bash
cd ../src  
python main.py
```

Both can coexist during migration.

### Step 8: Test the Workflow

#### Test via Slack

1. Go to your Slack workspace
2. Run `/aws-det-poc` to open the intake form
3. Fill in the form with test data:
   - Project name: "TestProject"
   - Environments: Dev
   - Region: us-east-1
   - VPC: Small
   - Terraform repo: (select from dropdown)
   - Team channel: (select your channel)
   - Service name: "Test Service"
   - Business justification: "Testing new workflow"
   - Team DL: your-email@example.com

4. Click Submit
5. You should see: "Onboarding workflow started successfully!"
6. Check the execution progress

#### Test via API (Direct)

```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "intake": {
      "project_name": "TestProject",
      "terraform_repo": "your-org/test-repo",
      "team_channel": "C0123456789",
      "environments": ["Dev"],
      "regions": ["us-east-1"],
      "vpc_model": "Small",
      "service_name": "Test Service",
      "business_justification": "Testing",
      "team_dl": "team@example.com",
      "workspace_mode": "default",
      "workspace_names": {}
    },
    "slack_channel": "C0123456789",
    "slack_user": "U0123456789"
  }'
```

Expected response:
```json
{
  "executionArn": "arn:aws:states:us-east-1:123456789012:execution:det-onboarding-prod-onboarding:abc123",
  "startDate": "2024-01-01T00:00:00.000Z",
  "message": "Onboarding workflow started successfully"
}
```

### Step 9: Monitor Execution

#### Via AWS Console

1. Go to AWS Step Functions console
2. Find `det-onboarding-prod-onboarding` state machine
3. Click on recent executions
4. View execution graph with status of each step

#### Via AWS CLI

```bash
# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn $(terraform output -raw state_machine_arn) \
  --max-results 10

# Describe specific execution
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn <execution-arn>
```

#### Via CloudWatch Logs

```bash
# Step Functions logs
aws logs tail /aws/states/det-onboarding-prod-onboarding --follow

# Individual Lambda logs
aws logs tail /aws/lambda/det-onboarding-prod-validate-intake --follow
aws logs tail /aws/lambda/det-onboarding-prod-github-branch --follow
aws logs tail /aws/lambda/det-onboarding-prod-github-commit --follow
aws logs tail /aws/lambda/det-onboarding-prod-hcp-project --follow
aws logs tail /aws/lambda/det-onboarding-prod-hcp-workspace --follow
aws logs tail /aws/lambda/det-onboarding-prod-hcp-vars --follow
```

## Workflow Steps

The Step Functions workflow executes the following steps:

1. **ValidateIntake** (Lambda)
   - Validates and normalizes intake data
   - Checks required fields
   - Returns validation errors if any
   - Retry: 2 attempts

2. **CreateGitHubBranch** (Lambda)
   - Creates feature branch in GitHub repo
   - Branch name derived from project name
   - Retry: 3 attempts

3. **CommitToGitHub** (Lambda)
   - Commits intake JSON document
   - File path: `requests/<project-slug>-<env>.json`
   - Retry: 3 attempts

4. **CreateHCPProject** (Lambda)
   - Creates HCP Terraform project
   - Project name from intake data
   - Retry: 3 attempts

5. **CreateWorkspaces** (Parallel Map)
   - Creates workspace for each environment
   - Runs in parallel (max 3 concurrent)
   - Independent retry: 3 attempts per workspace

6. **ConfigureVariables** (Parallel Map)
   - Configures variables for each workspace
   - Sets TFC_AWS_PROVIDER_AUTH and TFC_AWS_RUN_ROLE_ARN
   - Runs in parallel (max 3 concurrent)
   - Independent retry: 2 attempts per workspace

## Benefits of New Architecture

### 1. Retry Logic
Each step retries independently. Example:
- If GitHub commit fails temporarily (rate limit), it retries 3 times
- If successful on 2nd attempt, workflow continues
- Old architecture would have failed completely

### 2. Parallel Execution
Workspaces are created in parallel:
- 3 environments: Dev, QA, Prod
- All 3 workspaces created simultaneously
- Total time: ~time for slowest workspace (not sum of all)

### 3. Error Isolation
If one workspace fails:
- Other workspaces continue processing
- Failed workspace marked in results
- Partial success is possible

### 4. Observability
- Each step logged independently
- CloudWatch dashboards show step-by-step progress
- Easy to identify which step failed

### 5. Scalability
- Lambda auto-scales with demand
- No server management required
- Cost-effective (pay per execution)

## Rollback Plan

If you need to rollback to the original architecture:

1. Stop using `main_with_api_gateway.py`
2. Use original `main.py`
3. Keep Terraform infrastructure (for future use)
4. Or destroy infrastructure:

```bash
cd terraform
terraform destroy
```

## Updating the Infrastructure

### Update Lambda Function Code

1. Modify code in `lambda_functions/<function-name>/handler.py`
2. Apply changes:

```bash
cd terraform
terraform apply
```

Terraform detects code changes and updates the Lambda functions.

### Update Shared Layer

1. Modify shared code in `lambda_functions/shared_layer/python/`
2. Apply changes:

```bash
cd terraform  
terraform apply -target=aws_lambda_layer_version.shared_layer
```

Lambda functions automatically use the new layer on next cold start.

### Update Step Functions Definition

1. Modify `terraform/step_functions.tf`
2. Apply changes:

```bash
cd terraform
terraform apply
```

New executions use the updated state machine definition.

## Cost Optimization

Estimated monthly cost for 1000 onboarding requests: **~$2.24**

Breakdown:
- Lambda: ~$0.20 (6 functions × 1000 invocations)
- Step Functions: ~$0.25 (1000 executions)
- API Gateway: ~$0.04 (1000 requests)
- DynamoDB: ~$1.25 (on-demand)
- CloudWatch Logs: ~$0.50 (1 GB storage)

To optimize:
- Reduce Lambda memory if not needed (current: 512 MB)
- Reduce CloudWatch log retention (current: 14 days)
- Use reserved concurrency for predictable workloads

## Troubleshooting

### Issue: API Gateway returns 502

**Cause**: Step Functions cannot be invoked

**Solution**:
1. Check IAM role for API Gateway
2. Verify Step Functions ARN in integration
3. Check CloudWatch logs: `/aws/apigateway/det-onboarding-prod`

### Issue: Lambda function timeout

**Cause**: Function exceeds 60-second timeout

**Solution**:
1. Increase timeout in `terraform/variables.tf`:
   ```hcl
   lambda_timeout = 120
   ```
2. Apply: `terraform apply`

### Issue: Validation fails

**Cause**: Missing required fields in intake data

**Solution**:
1. Check validation errors in Lambda logs
2. Verify all required fields are provided:
   - project_name, terraform_repo, team_channel
   - environments, regions, vpc_model
   - service_name, business_justification, team_dl

### Issue: GitHub API rate limit

**Cause**: Too many API requests

**Solution**:
- Step Functions retries automatically with exponential backoff
- Check retry attempts in execution history
- Consider GitHub App installation ID instead of OAuth token

### Issue: HCP Terraform workspace creation fails

**Cause**: Missing VCS configuration or branch doesn't exist

**Solution**:
1. Verify `HCP_TERRAFORM_VCS_OAUTH_TOKEN_ID` is set
2. Check branch exists in Terraform repo
3. Verify HCP Terraform organization name

## Support

For issues:
1. Check CloudWatch Logs for error details
2. Review Step Functions execution history
3. Verify environment variables in Lambda functions
4. Check IAM permissions
5. Review Terraform state: `terraform show`

## Next Steps

After successful deployment:

1. **Production Readiness**
   - Add API Gateway authorization (AWS_IAM or custom authorizer)
   - Set up SNS notifications for CloudWatch alarms
   - Configure VPC for Lambda functions if needed
   - Use AWS Secrets Manager for sensitive variables

2. **Enhanced Monitoring**
   - Create CloudWatch dashboard
   - Set up X-Ray tracing
   - Add custom metrics

3. **CI/CD**
   - Automate Terraform deployments
   - Set up testing pipeline for Lambda functions
   - Implement blue/green deployments

4. **Documentation**
   - Document runbooks for common issues
   - Create architecture diagrams
   - Set up team training

## References

- [Architecture Documentation](docs/step-functions-architecture.md)
- [Terraform README](terraform/README.md)
- [AWS Step Functions Best Practices](https://docs.aws.amazon.com/step-functions/latest/dg/best-practices.html)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
