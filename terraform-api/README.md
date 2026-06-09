# Terraform Infrastructure for DET Onboarding

This directory contains Terraform configurations for deploying the AWS infrastructure for the DET onboarding workflow.

## Architecture

The infrastructure consists of:
- **Lambda Functions**: 6 Lambda functions for independent workflow steps
- **Lambda Layer**: Shared code layer for common utilities
- **Step Functions**: State machine orchestrating the workflow
- **API Gateway**: REST API for triggering workflows
- **DynamoDB**: Execution tracking and status storage
- **IAM Roles**: Least-privilege roles for each service
- **CloudWatch**: Logging and monitoring for all components

## Prerequisites

1. **Terraform**: Version 1.5.0 or later
2. **AWS CLI**: Configured with appropriate credentials
3. **AWS Account**: With permissions to create the required resources
4. **Environment Variables/Secrets**:
   - GitHub token with repo access
   - HCP Terraform API token
   - Slack bot token

## Directory Structure

```
terraform/
├── main.tf                 # Provider and backend configuration
├── variables.tf            # Input variable definitions
├── outputs.tf              # Output values
├── terraform.tfvars.example # Example variable values
├── iam.tf                  # IAM roles and policies
├── lambda_functions.tf     # Lambda function definitions
├── lambda_layer.tf         # Lambda layer configuration
├── step_functions.tf       # Step Functions state machine
├── api_gateway.tf          # API Gateway REST API
├── dynamodb.tf             # DynamoDB table for execution tracking
└── README.md               # This file
```

## Setup Instructions

### 1. Configure Variables

Copy the example tfvars file and fill in your values:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your actual values:
- AWS region
- GitHub credentials and repository
- HCP Terraform credentials and organization
- Slack bot token
- Project configuration

**Important**: Never commit `terraform.tfvars` to version control as it contains sensitive data.

### 2. Configure Backend (Optional but Recommended)

For production, configure remote state storage in `main.tf`:

```hcl
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "det-onboarding/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

### 3. Initialize Terraform

```bash
cd terraform
terraform init
```

This will:
- Download required provider plugins
- Initialize the backend
- Validate the configuration

### 4. Review the Plan

```bash
terraform plan
```

Review the execution plan to ensure:
- Correct resources are being created
- No unexpected changes or deletions
- Variable values are correct

### 5. Apply the Configuration

```bash
terraform apply
```

Type `yes` when prompted to confirm the changes.

This will create:
- 6 Lambda functions
- 1 Lambda layer
- 1 Step Functions state machine
- 1 API Gateway REST API
- 1 DynamoDB table
- Multiple IAM roles and policies
- CloudWatch log groups
- CloudWatch alarms

Deployment typically takes 3-5 minutes.

### 6. Capture Outputs

After successful deployment, note the outputs:

```bash
terraform output
```

Important outputs:
- `api_gateway_url`: Endpoint for triggering workflows
- `state_machine_arn`: Step Functions ARN
- `dynamodb_table_name`: Table for execution tracking

### 7. Configure Slack App

Update your Slack application environment variables with the API Gateway URL:

```bash
export API_GATEWAY_ENDPOINT="<api_gateway_url from outputs>"
```

## Deployment Scripts

### Package Lambda Functions

The Lambda functions are automatically packaged during `terraform apply`. The archive provider zips each function directory.

To manually verify packaging:

```bash
# Check Lambda function code
ls -lh terraform/*.zip

# View Lambda layer contents
unzip -l terraform/lambda_layer.zip
```

### Update Lambda Functions Only

To update just the Lambda functions without affecting other resources:

```bash
terraform apply -target=aws_lambda_function.validate_intake \
                -target=aws_lambda_function.github_branch \
                -target=aws_lambda_function.github_commit \
                -target=aws_lambda_function.hcp_project \
                -target=aws_lambda_function.hcp_workspace \
                -target=aws_lambda_function.hcp_vars
```

### Update Lambda Layer Only

```bash
terraform apply -target=aws_lambda_layer_version.shared_layer
```

Note: After updating the layer, Lambda functions automatically pick up the new version on their next cold start.

## Testing

### Test API Gateway Endpoint

```bash
curl -X POST <api_gateway_url> \
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
      "team_dl": "team@example.com"
    },
    "slack_channel": "C0123456789",
    "slack_user": "U0123456789"
  }'
```

Expected response:
```json
{
  "executionArn": "arn:aws:states:...:execution:...",
  "startDate": "2024-01-01T00:00:00.000Z",
  "message": "Onboarding workflow started successfully"
}
```

### Check Execution Status

```bash
EXECUTION_ARN="<execution_arn from above>"
curl -X GET "<api_status_url>/${EXECUTION_ARN}"
```

### Test Individual Lambda Functions

```bash
# Test validate_intake Lambda
aws lambda invoke \
  --function-name det-onboarding-prod-validate-intake \
  --payload '{"intake": {"project_name": "Test"}}' \
  response.json

cat response.json
```

## Monitoring

### CloudWatch Logs

View logs for each component:

```bash
# Lambda function logs
aws logs tail /aws/lambda/det-onboarding-prod-validate-intake --follow

# Step Functions logs
aws logs tail /aws/states/det-onboarding-prod-onboarding --follow

# API Gateway logs
aws logs tail /aws/apigateway/det-onboarding-prod --follow
```

### CloudWatch Metrics

Monitor key metrics:
- Lambda function invocations, errors, duration
- Step Functions execution success/failure rates
- API Gateway request counts, 4xx/5xx errors
- DynamoDB read/write capacity

### CloudWatch Alarms

The following alarms are configured:
- Step Functions failed executions (threshold: 5 in 5 minutes)
- Step Functions throttled executions (threshold: 3 in 5 minutes)
- DynamoDB read throttle events (threshold: 10 in 5 minutes)
- DynamoDB write throttle events (threshold: 10 in 5 minutes)

## Cost Estimation

Estimated monthly costs (assuming 1000 onboarding requests/month):

| Service | Cost |
|---------|------|
| Lambda (6 functions × 1000 invocations) | ~$0.20 |
| Step Functions (1000 state transitions) | ~$0.25 |
| API Gateway (1000 requests) | ~$0.04 |
| DynamoDB (on-demand) | ~$1.25 |
| CloudWatch Logs (1 GB/month) | ~$0.50 |
| **Total** | **~$2.24/month** |

*Note: Costs will scale with usage. Add CloudWatch alarms SNS notifications if needed (~$0.50/month).*

## Updating Infrastructure

### Update Lambda Code

1. Modify Lambda function code in `../lambda_functions/`
2. Run `terraform apply` to redeploy

### Update Shared Layer

1. Modify shared code in `../lambda_functions/shared_layer/python/`
2. Run `terraform apply -target=aws_lambda_layer_version.shared_layer`
3. Update Lambda functions to pick up the new layer

### Update Step Functions Definition

1. Modify state machine definition in `step_functions.tf`
2. Run `terraform apply`
3. New executions will use the updated definition

### Update Environment Variables

1. Modify variables in `terraform.tfvars`
2. Run `terraform apply`
3. Lambda functions will receive new environment variables on next invocation

## Cleanup

To destroy all infrastructure:

```bash
terraform destroy
```

**Warning**: This will permanently delete:
- All Lambda functions and layers
- Step Functions state machine (but not execution history)
- API Gateway (endpoint will stop working)
- DynamoDB table (all execution data will be lost)
- All CloudWatch logs

Make sure to:
1. Export any important execution history from DynamoDB
2. Download CloudWatch logs if needed for audit
3. Verify no active executions are running

## Troubleshooting

### Lambda Function Errors

Check CloudWatch Logs for the specific function:
```bash
aws logs tail /aws/lambda/det-onboarding-prod-<function-name> --follow
```

Common issues:
- Missing environment variables
- IAM permission errors
- Timeout errors (increase timeout in `variables.tf`)
- Memory errors (increase memory_size in `variables.tf`)

### Step Functions Failures

View execution details:
```bash
aws stepfunctions describe-execution --execution-arn <arn>
```

Check execution history:
```bash
aws stepfunctions get-execution-history --execution-arn <arn>
```

### API Gateway 502/503 Errors

- Check IAM role has permission to invoke Step Functions
- Verify Step Functions state machine ARN in integration
- Check API Gateway CloudWatch logs

### DynamoDB Throttling

If you see throttling alarms:
- Consider switching from on-demand to provisioned capacity
- Increase read/write capacity units
- Review query patterns and add indexes if needed

## Security Considerations

1. **Secrets Management**: Consider using AWS Secrets Manager for sensitive values
2. **API Authorization**: Add AWS_IAM or custom authorizer to API Gateway
3. **Network**: Deploy Lambda functions in VPC if needed
4. **Encryption**: DynamoDB encryption at rest is enabled by default
5. **Least Privilege**: IAM roles follow least-privilege principle

## Support

For issues or questions:
1. Check CloudWatch Logs for error details
2. Review Step Functions execution history
3. Consult the main project README
4. Check AWS service limits (Lambda concurrency, Step Functions executions)

## References

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS Step Functions Documentation](https://docs.aws.amazon.com/step-functions/)
- [API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
