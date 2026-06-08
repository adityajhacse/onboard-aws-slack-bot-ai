# Terraform Infrastructure - Quick Reference

## ✨ Recent Updates

### New Lambda Functions
1. **`status_lookup`** - API endpoint for Service Request ID lookups
2. **`validation_notifier`** - Immediate Slack notifications

### New API Endpoint
- **GET `/status`** - Query by Service Request ID

---

## Deploy Everything

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

After deployment:
```bash
# Get the Status API URL
terraform output status_api_url

# Configure your bot
export STATUS_API_URL=$(terraform output -raw status_api_url)
```

---

## File Locations

### New Lambda Functions
- `terraform/modules/lambda/lambda_functions/status_lookup/handler.py`
- `terraform/modules/lambda/lambda_functions/validation_notifier/handler.py`

### Updated Lambda Functions
- `terraform/modules/lambda/lambda_functions/shared_layer/python/dynamodb_helper.py`
- `terraform/modules/lambda/lambda_functions/status_tracker/handler.py`
- `terraform/modules/lambda/lambda_functions/completion_notifier/handler.py`

---

## Quick Test

```bash
# Get your API URL
API_URL=$(terraform output -raw status_api_url)

# Test with a real Service Request ID
curl "${API_URL}?service_request_id=SR-20260608-1408"
```

---

## Documentation

- **Full Guide:** `TERRAFORM_DEPLOYMENT.md`
- **Architecture:** `../docs/ARCHITECTURE.md`
- **Implementation:** `../src/FINAL_SUMMARY.md`

---

**Ready to deploy!** 🚀
