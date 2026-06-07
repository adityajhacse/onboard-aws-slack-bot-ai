# Default Workspace Names

## Overview

When users don't provide custom workspace names, the system automatically generates default names.

---

## Default Naming Convention

**Format:** `{project-slug}-{environment}`

**Examples:**

| Project Slug | Environment | Workspace Name |
|--------------|-------------|----------------|
| `myapp` | `Dev` | `myapp-dev` |
| `myapp` | `Staging` | `myapp-staging` |
| `myapp` | `Prod` | `myapp-prod` |
| `api-service` | `Dev` | `api-service-dev` |
| `api-service` | `Prod` | `api-service-prod` |

---

## How It Works

### 1. User Submits Form

User fills out the Slack form with:
- Project name: `MyApp`
- Environments: `Dev`, `Staging`, `Prod`
- **Workspace names:** *(left empty or not provided)*

### 2. System Generates Defaults

The `validate_intake` Lambda function automatically generates:

```json
{
  "project_slug": "myapp",
  "environments": ["Dev", "Staging", "Prod"],
  "workspace_names": {
    "Dev": "myapp-dev",
    "Staging": "myapp-staging",
    "Prod": "myapp-prod"
  }
}
```

### 3. Workspaces Created

The `hcp_workspace` Lambda creates workspaces with these default names.

---

## Code Logic

### validate_intake Lambda

```python
# Generate default workspace names if not provided
workspace_names = validated_intake.get('workspace_names', {})

if not workspace_names or workspace_names == {}:
    project_slug = validated_intake.get('project_slug', '').lower()
    environments = validated_intake.get('environments', [])
    
    # Generate default workspace names: {project-slug}-{env}
    default_workspace_names = {}
    for env in environments:
        env_lower = env.lower()
        default_workspace_names[env] = f"{project_slug}-{env_lower}"
    
    validated_intake['workspace_names'] = default_workspace_names
```

### hcp_workspace Lambda

```python
# Get workspace name for this environment
if workspace_names and environment in workspace_names:
    workspace_name = workspace_names[environment]
else:
    # Generate default workspace name
    workspace_name = f"{project_slug}-{environment.lower()}"
```

---

## Custom Workspace Names

Users can still provide custom workspace names in the form if they want to override the defaults.

**Example custom names:**

```json
{
  "workspace_names": {
    "Dev": "mycompany-myapp-development",
    "Staging": "mycompany-myapp-staging",
    "Prod": "mycompany-myapp-production"
  }
}
```

---

## Workspace Name Rules

Default workspace names follow these rules:

1. **Lowercase:** All environment names converted to lowercase
2. **Hyphenated:** Format is `{slug}-{env}`
3. **Project slug:** Uses the sanitized project slug
4. **Environment:** Uses the lowercase environment name

**Valid examples:**
- ✅ `myapp-dev`
- ✅ `api-service-prod`
- ✅ `customer-portal-staging`

**Invalid (won't be generated):**
- ❌ `MyApp-Dev` (uppercase)
- ❌ `myapp_dev` (underscore)
- ❌ `myapp dev` (space)

---

## Benefits

### ✅ User-Friendly
Users don't need to think about workspace naming conventions

### ✅ Consistent
All workspaces follow the same naming pattern

### ✅ Predictable
Easy to know what a workspace is for: `{project}-{env}`

### ✅ Flexible
Users can still override with custom names if needed

---

## Example Flow

### User Input (Slack Form)
```
Project Name: Customer Portal
Environments: Dev, Prod
Workspace Names: [empty]
```

### System Processing
```json
{
  "project_name": "Customer Portal",
  "project_slug": "customer-portal",
  "environments": ["Dev", "Prod"],
  "workspace_names": {}  // Empty!
}
```

### After validate_intake
```json
{
  "project_name": "Customer Portal",
  "project_slug": "customer-portal",
  "environments": ["Dev", "Prod"],
  "workspace_names": {
    "Dev": "customer-portal-dev",
    "Prod": "customer-portal-prod"
  }  // Auto-generated!
}
```

### Result in HCP Terraform
- ✅ Workspace created: `customer-portal-dev`
- ✅ Workspace created: `customer-portal-prod`

---

## Testing

### Test with Empty Workspace Names

```bash
# Submit via API Gateway
curl -X POST "$API_GATEWAY_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "intake": {
      "project_name": "TestApp",
      "project_slug": "testapp",
      "environments": ["Dev", "Prod"],
      "workspace_names": {}
    },
    "slack_channel": "C123",
    "slack_user": "U456"
  }'
```

**Expected:**
- Workspaces created: `testapp-dev`, `testapp-prod`

### Check Logs

```bash
aws logs tail /aws/lambda/det-onboarding-prod-validate-intake --follow
```

Look for:
```
Generated default workspace names: {'Dev': 'testapp-dev', 'Prod': 'testapp-prod'}
```

---

## Deployment

The fix is in the Lambda function code. To deploy:

```bash
cd terraform
terraform apply
```

This updates the Lambda functions with the new default workspace logic.

---

## Rollback

If you need to revert to requiring explicit workspace names:

1. Remove the default generation logic from `validate_intake/handler.py`
2. Redeploy: `terraform apply`

---

## Summary

✅ **Empty workspace_names** → System generates defaults  
✅ **Format:** `{project-slug}-{environment}`  
✅ **Custom names** → Still supported if provided  
✅ **User-friendly** → No need to specify workspace names  

**Example:** Project `MyApp` with environments `Dev`, `Prod` → Creates `myapp-dev` and `myapp-prod` ✅
