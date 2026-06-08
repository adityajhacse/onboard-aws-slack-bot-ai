#!/bin/bash
#
# Deploy Status Tracking Updates
#
# This script deploys the Lambda functions and Step Functions state machine
# with real-time status tracking for all workflow steps.
#

set -e

echo "========================================="
echo "Deploying Status Tracking Updates"
echo "========================================="
echo ""

# Change to terraform directory
cd "$(dirname "$0")"

echo "✓ Working directory: $(pwd)"
echo ""

# Step 1: Taint the shared layer to force rebuild
echo "Step 1: Tainting shared Lambda layer..."
terraform taint module.lambda.aws_lambda_layer_version.shared_layer || echo "  (Layer not found or already tainted)"
echo ""

# Step 2: Run terraform plan
echo "Step 2: Planning deployment..."
terraform plan -out=tfplan
echo ""

# Step 3: Apply the plan
echo "Step 3: Applying changes..."
terraform apply tfplan
rm -f tfplan
echo ""

echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "What was deployed:"
echo "  • Updated shared Lambda layer with status tracking"
echo "  • Updated Lambda functions:"
echo "    - github_branch (tracks CreateGitHubBranch)"
echo "    - github_commit (tracks CommitToGitHub)"
echo "    - hcp_project (tracks CreateHCPProject)"
echo "    - hcp_workspace (records workspace results)"
echo "  • Updated Step Functions state machine:"
echo "    - Added TrackWorkspacesSuccess step"
echo "    - Added TrackVariablesSuccess step"
echo "    - Added execution_id to all Task parameters"
echo ""
echo "Next steps:"
echo "  1. Test with a new onboarding request"
echo "  2. Check status with: /aws-det-onboard-status SR-YYYYMMDD-XXXX"
echo "  3. All steps should now update in real-time!"
echo ""
