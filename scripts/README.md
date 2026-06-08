# Setup Scripts

This folder contains one-time setup and utility scripts.

## get_hcp_vcs_oauth_token_id.py

**Purpose:** Retrieve the HCP Terraform VCS OAuth Token ID for your organization.

**When to use:** During initial setup of the infrastructure, before running `terraform apply`.

**Usage:**

```bash
# Set your HCP Terraform token
export HCP_TERRAFORM_TOKEN="your-token-here"

# Run the script
python3 scripts/get_hcp_vcs_oauth_token_id.py --org your-org-name
```

**Output:**
```
Found OAuth clients:

- client_id: oc-xxxxx
  service_provider: github
  http_url: https://github.com
  api_url: https://api.github.com
  oauth_token_ids: ot-xxxxx
  export command examples:
    export HCP_TERRAFORM_VCS_OAUTH_TOKEN_ID="ot-xxxxx"
```

**Next steps:**
1. Copy the `ot-xxxxx` value
2. Add it to your `terraform/terraform.tfvars`:
   ```hcl
   hcp_terraform_vcs_oauth_token_id = "ot-xxxxx"
   ```

---

**Note:** This script is NOT part of the Slack bot runtime. It's a one-time setup utility.
