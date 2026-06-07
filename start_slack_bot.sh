#!/bin/bash
#
# Start the Slack bot with Step Functions integration
#

set -e

echo "======================================"
echo "Starting DET Onboarding Slack Bot"
echo "======================================"
echo ""

# Check if we're in the project root
if [ ! -d "terraform" ] || [ ! -d "src" ]; then
    echo "Error: Must run from project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Get API Gateway URL from Terraform
echo "📡 Getting API Gateway endpoint from Terraform..."
cd terraform

if [ ! -f "terraform.tfstate" ]; then
    echo ""
    echo "⚠️  Warning: Terraform state not found"
    echo "Have you deployed the infrastructure yet?"
    echo ""
    echo "Run these commands first:"
    echo "  cd terraform"
    echo "  terraform init"
    echo "  terraform apply"
    echo ""
    exit 1
fi

API_URL=$(terraform output -raw api_gateway_url 2>/dev/null)
cd ..

if [ -z "$API_URL" ]; then
    echo ""
    echo "❌ Error: Could not get API Gateway URL from Terraform"
    echo ""
    echo "Make sure infrastructure is deployed:"
    echo "  cd terraform && terraform output api_gateway_url"
    echo ""
    exit 1
fi

echo "✅ API Gateway URL: $API_URL"
echo ""

# Export environment variable
export API_GATEWAY_ENDPOINT="$API_URL"

# Check if Slack tokens are set
if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "⚠️  Warning: SLACK_BOT_TOKEN not set"
    echo "Make sure you have set all required environment variables:"
    echo "  - SLACK_BOT_TOKEN"
    echo "  - SLACK_APP_TOKEN"
    echo ""
fi

# Start the bot
echo "🚀 Starting Slack bot..."
echo ""
cd src

if [ ! -f "main_with_api_gateway.py" ]; then
    echo "❌ Error: main_with_api_gateway.py not found"
    exit 1
fi

echo "Using: main_with_api_gateway.py"
echo "API Gateway: $API_GATEWAY_ENDPOINT"
echo ""
echo "Bot is running. Press Ctrl+C to stop."
echo "======================================"
echo ""

python main_with_api_gateway.py
