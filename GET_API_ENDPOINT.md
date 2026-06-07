# How to Get API_GATEWAY_ENDPOINT

## The Issue

When starting the Slack bot, you get:
```
ValueError: API_GATEWAY_ENDPOINT environment variable is required
```

This is because the Slack bot needs to know the API Gateway URL to call Lambda functions.

---

## Solution: Deploy Terraform First

The `API_GATEWAY_ENDPOINT` is created by Terraform. You must deploy infrastructure **before** starting the Slack bot.

---

## Step-by-Step

### Step 1: Deploy Terraform Infrastructure

```bash
cd terraform
terraform init
terraform apply
```

**Type `yes` when prompted.**

This will create:
- API Gateway REST API
- Lambda functions
- Step Functions
- DynamoDB tables
- All other infrastructure

**Time:** ~2-3 minutes

### Step 2: Get the API Gateway URL

After `terraform apply` completes, get the URL:

```bash
terraform output api_gateway_url
```

**Example output:**
```
"https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/onboard"
```

Copy this URL (without quotes).

### Step 3: Set Environment Variable

#### Option A: Set Manually
```bash
export API_GATEWAY_ENDPOINT="https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/onboard"
```

Replace with **your actual URL** from Step 2.

#### Option B: Use Startup Script (Recommended)

The startup script does this automatically:

```bash
cd ..  # Go back to project root
./start_slack_bot.sh
```

The script will:
1. Automatically read the URL from Terraform
2. Set `API_GATEWAY_ENDPOINT`
3. Start the Slack bot

---

## Quick Commands

### If Terraform is NOT deployed yet:

```bash
# 1. Deploy infrastructure
cd terraform
terraform apply

# 2. Go back to root
cd ..

# 3. Start bot (auto-gets API endpoint)
./start_slack_bot.sh
```

### If Terraform IS already deployed:

```bash
# Get the URL
cd terraform
terraform output api_gateway_url

# Set it and start bot
cd ..
export API_GATEWAY_ENDPOINT="<URL from above>"
python3 src/main_with_api_gateway.py
```

Or just use the startup script:
```bash
./start_slack_bot.sh
```

---

## The Startup Script Does This Automatically

The `start_slack_bot.sh` script already handles this:

```bash
#!/bin/bash

# Get API Gateway URL from Terraform
if [ -d "terraform" ]; then
    cd terraform
    API_URL=$(terraform output -raw api_gateway_url 2>/dev/null)
    cd ..
    
    if [ -n "$API_URL" ]; then
        export API_GATEWAY_ENDPOINT="$API_URL"
        echo "✓ API Gateway endpoint: $API_GATEWAY_ENDPOINT"
    else
        echo "⚠ Could not get API Gateway URL from Terraform"
        echo "Run: cd terraform && terraform apply"
        exit 1
    fi
fi

# Start Slack bot
python3 src/main_with_api_gateway.py
```

---

## Verification

After setting the environment variable, verify it:

```bash
echo $API_GATEWAY_ENDPOINT
```

Should show:
```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/onboard
```

Then start the bot:
```bash
python3 src/main_with_api_gateway.py
```

---

## Complete First-Time Setup

If this is your first time setting up:

```bash
# 1. Configure tokens in terraform.tfvars
cd terraform
vim terraform.tfvars  # Edit with your tokens

# 2. Deploy infrastructure
terraform init
terraform apply

# 3. Verify API Gateway URL
terraform output api_gateway_url

# 4. Go back to root
cd ..

# 5. Start bot (uses startup script)
./start_slack_bot.sh
```

---

## What If I Don't Have Terraform Deployed?

You **MUST** deploy Terraform first. The Slack bot cannot work without the API Gateway and Lambda functions.

**Order:**
1. ✅ Deploy Terraform (`terraform apply`)
2. ✅ Get API Gateway URL (automatic or `terraform output`)
3. ✅ Start Slack bot (`./start_slack_bot.sh`)

You cannot skip step 1!

---

## Troubleshooting

### Error: "Could not get API Gateway URL from Terraform"

**Cause:** Terraform not deployed yet

**Solution:**
```bash
cd terraform
terraform apply
```

### Error: "terraform output -raw api_gateway_url returns empty"

**Cause:** Terraform applied but API Gateway not created

**Solution:** Check Terraform outputs:
```bash
cd terraform
terraform output
```

You should see `api_gateway_url` in the list.

### Error: "Module not found" when running Slack bot

**Cause:** Missing Python dependencies

**Solution:**
```bash
pip3 install -r requirements.txt
```

---

## Summary

**The API Gateway URL comes from Terraform after deployment.**

**Quick Start:**
```bash
cd terraform
terraform apply
cd ..
./start_slack_bot.sh
```

Done! ✅
