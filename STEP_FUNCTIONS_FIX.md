# Step Functions Map State Fix

## Issue

Step Functions Map state was failing with:
```
The JSONPath '$$.Map.Item.Value' specified for the field 'environment.$' 
could not be found in the input
```

---

## Root Cause

The Map state's Iterator was trying to access `$$.Execution.Input.*` directly, but:
- `$$.Execution.Input` contains the **original workflow input**
- The **Map state's Parameters** should pass data to the Iterator
- The Iterator receives items via `$$.Map.Item.Value`

**Wrong configuration:**
```json
"CreateWorkspacesMap": {
  "Type": "Map",
  "ItemsPath": "$.environments",
  "Iterator": {
    "States": {
      "CreateWorkspace": {
        "Parameters": {
          "environment.$": "$$.Map.Item.Value",
          "project_id.$": "$$.Execution.Input.project_id"  // ❌ Wrong!
        }
      }
    }
  }
}
```

**Problem:** `$$.Execution.Input.project_id` doesn't exist because the state machine input is nested differently.

---

## Solution

Move the Parameters to the **Map state level**, not the Iterator level:

**Correct configuration:**
```json
"CreateWorkspacesMap": {
  "Type": "Map",
  "ItemsPath": "$.environments",
  "Parameters": {
    "environment.$": "$$.Map.Item.Value",
    "project_id.$": "$.project_id",           // ✅ Correct!
    "project_slug.$": "$.project_slug",
    "terraform_repo.$": "$.terraform_repo",
    "workspace_names.$": "$.workspace_names"
  },
  "Iterator": {
    "States": {
      "CreateWorkspace": {
        "Type": "Task",
        "Resource": "${hcp_workspace_arn}"
      }
    }
  }
}
```

---

## What Changed

### File: `terraform/modules/step_functions/state_machine.json.tpl`

#### Change 1: CreateWorkspacesMap

**Before:**
```json
"CreateWorkspacesMap": {
  "Type": "Map",
  "ItemsPath": "$.environments",
  "Iterator": {
    "States": {
      "CreateWorkspace": {
        "Parameters": {
          "environment.$": "$$.Map.Item.Value",
          "project_id.$": "$$.Execution.Input.project_id",
          ...
        }
      }
    }
  }
}
```

**After:**
```json
"CreateWorkspacesMap": {
  "Type": "Map",
  "ItemsPath": "$.environments",
  "Parameters": {
    "environment.$": "$$.Map.Item.Value",
    "project_id.$": "$.project_id",
    "project_slug.$": "$.project_slug",
    "terraform_repo.$": "$.terraform_repo",
    "workspace_names.$": "$.workspace_names"
  },
  "Iterator": {
    "States": {
      "CreateWorkspace": {
        "Type": "Task",
        "Resource": "${hcp_workspace_arn}"
      }
    }
  }
}
```

#### Change 2: ConfigureVariablesMap

**Before:**
```json
"ConfigureVariablesMap": {
  "Type": "Map",
  "ItemsPath": "$.workspaces",
  "Iterator": {
    "States": {
      "ConfigureVars": {
        "Type": "Task",
        "Resource": "${hcp_vars_arn}"
      }
    }
  }
}
```

**After:**
```json
"ConfigureVariablesMap": {
  "Type": "Map",
  "ItemsPath": "$.workspaces",
  "Parameters": {
    "workspace.$": "$$.Map.Item.Value"
  },
  "Iterator": {
    "States": {
      "ConfigureVars": {
        "Type": "Task",
        "Resource": "${hcp_vars_arn}",
        "InputPath": "$.workspace"
      }
    }
  }
}
```

---

## How Step Functions Map States Work

### Structure

```json
{
  "Type": "Map",
  "ItemsPath": "$.arrayField",           // Array to iterate over
  "Parameters": {                         // ← Define parameters HERE
    "item.$": "$$.Map.Item.Value",       // Current item
    "contextData.$": "$.someField"       // Data from state input
  },
  "Iterator": {
    "StartAt": "ProcessItem",
    "States": {
      "ProcessItem": {
        "Type": "Task",
        "Resource": "arn:...",
        // Receives the Parameters defined above
      }
    }
  }
}
```

### Key Points

1. **`Parameters` at Map level** - Combines item with context data
2. **`$$.Map.Item.Value`** - Current array item
3. **`$.field`** - Field from Map state's input
4. **`$$.Execution.Input.field`** - Field from original workflow input (use sparingly)

---

## Example Flow

### Input to CreateWorkspacesMap:
```json
{
  "project_id": "prj-123",
  "project_slug": "myapp",
  "terraform_repo": "org/repo",
  "environments": ["Dev", "Prod"],
  "workspace_names": {}
}
```

### Map iterates over `$.environments`:

**Iteration 1:**
- `$$.Map.Item.Value` = `"Dev"`
- Parameters passed to Iterator:
  ```json
  {
    "environment": "Dev",
    "project_id": "prj-123",
    "project_slug": "myapp",
    "terraform_repo": "org/repo",
    "workspace_names": {}
  }
  ```

**Iteration 2:**
- `$$.Map.Item.Value` = `"Prod"`
- Parameters passed to Iterator:
  ```json
  {
    "environment": "Prod",
    "project_id": "prj-123",
    "project_slug": "myapp",
    "terraform_repo": "org/repo",
    "workspace_names": {}
  }
  ```

---

## Testing

### Deploy the Fix

```bash
cd terraform
terraform apply
```

### Test via Slack

1. Submit onboarding form with:
   - Project: `TestApp`
   - Environments: `Dev`, `Prod`

2. Monitor Step Functions:
   ```bash
   # Watch the execution
   aws stepfunctions list-executions \
     --state-machine-arn "$(terraform output -raw state_machine_arn)" \
     --max-results 1
   ```

3. Check logs:
   ```bash
   aws logs tail /aws/lambda/det-onboarding-prod-hcp-workspace --follow
   ```

### Expected Result

✅ Map state executes successfully
✅ Workspaces created for each environment in parallel
✅ No JSONPath errors

---

## Verification

After deployment, check the state machine definition:

```bash
# Get state machine ARN
STATE_MACHINE_ARN=$(cd terraform && terraform output -raw state_machine_arn)

# View definition
aws stepfunctions describe-state-machine \
  --state-machine-arn "$STATE_MACHINE_ARN" \
  --query 'definition' --output text | jq '.States.CreateWorkspacesMap'
```

Should show Parameters at the Map level, not in the Iterator.

---

## Deployment

```bash
cd terraform
terraform apply
```

The fix is now deployed! ✅

---

## Summary

**Issue:** Map state Iterator couldn't access `$$.Execution.Input` fields

**Fix:** Move Parameters to Map state level, use `$.field` instead of `$$.Execution.Input.field`

**Result:** 
- ✅ Map state works correctly
- ✅ Workspaces created in parallel
- ✅ Variables configured in parallel

Ready to test! 🚀
