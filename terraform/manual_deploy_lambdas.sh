#!/bin/bash
#
# Manual Lambda Deployment Script
# Use this when Terraform is not working due to provider issues
#

set -e

cd "$(dirname "$0")/modules/lambda/lambda_functions"

echo "========================================="
echo "Manual Lambda Deployment"
echo "========================================="
echo ""

# Function to zip and deploy a Lambda function
deploy_lambda() {
    local func_name=$1
    local func_dir=$2

    echo "📦 Deploying $func_name..."

    # Create temp directory for packaging
    temp_dir=$(mktemp -d)

    # Copy function code
    cp "$func_dir/handler.py" "$temp_dir/"

    # Copy shared layer dependencies
    if [ -d "shared_layer/python" ]; then
        cp -r shared_layer/python/* "$temp_dir/"
    fi

    # Create zip
    cd "$temp_dir"
    zip -q -r function.zip .

    # Deploy to AWS
    aws lambda update-function-code \
        --function-name "$func_name" \
        --zip-file fileb://function.zip \
        --region us-east-1

    # Wait for update to complete
    echo "   Waiting for deployment to complete..."
    aws lambda wait function-updated \
        --function-name "$func_name" \
        --region us-east-1

    # Cleanup
    cd - > /dev/null
    rm -rf "$temp_dir"

    echo "   ✅ $func_name deployed successfully"
    echo ""
}

# Deploy each Lambda function
deploy_lambda "det-onboarding-prod-github-branch" "github_branch"
deploy_lambda "det-onboarding-prod-github-commit" "github_commit"
deploy_lambda "det-onboarding-prod-hcp-project" "hcp_project"
deploy_lambda "det-onboarding-prod-hcp-workspace" "hcp_workspace"

echo "========================================="
echo "✅ All Lambda Functions Deployed!"
echo "========================================="
echo ""
echo "Test with a new onboarding request:"
echo "  /aws-det-onboard"
echo ""
echo "Then check status:"
echo "  /aws-det-onboard-status SR-YYYYMMDD-XXXX"
echo ""
