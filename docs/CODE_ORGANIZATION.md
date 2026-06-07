# Code Organization & Purpose

## Overview

This document explains the organization of source code files and the relationship between `src/` and Lambda function code.

---

## 📁 Directory Structure

```
Det-aws-cicd-project/
├── src/                                    # Slack Bot Runtime Code
│   ├── github_api.py                       # SOURCE FILE
│   ├── hcp_terraform.py                    # SOURCE FILE
│   ├── det_intake.py                       # SOURCE FILE
│   ├── main_with_api_gateway.py           # Slack bot entry point
│   └── ...
│
└── terraform/modules/lambda/
    └── lambda_functions/
        └── shared_layer/
            └── python/
                ├── github_api.py           # COPY (from src/)
                ├── hcp_terraform.py        # COPY (from src/)
                ├── det_intake.py           # COPY (from src/)
                └── dynamodb_helper.py      # Lambda-specific
```

---

## 🔍 Purpose of `src/github_api.py`

### What It Does

`github_api.py` provides GitHub API integration functions:

1. **Repository Operations:**
   - `list_org_repositories()` - Lists repositories in GitHub organization
   - `ensure_git_branch()` - Creates Git branch if it doesn't exist

2. **File Operations:**
   - `put_repository_json_file()` - Commits JSON file to repository
   - `build_github_intake_document()` - Creates AFT JSON structure

3. **Utility Functions:**
   - `sanitize_git_branch_from_project_name()` - Sanitizes branch names
   - Error handling with `GitHubApiError`

### Where It's Used

#### 1. **In `src/` - Slack Bot Code (Runtime)**

**Referenced by:**
- **`src/main_with_api_gateway.py`** (Line 18)
  ```python
  from github_api import GitHubApiError, list_org_repositories
  ```
  - **Purpose:** Lists GitHub repos for Slack modal dropdown

- **`src/det_intake.py`**
  ```python
  from github_api import build_github_intake_document, sanitize_git_branch_from_project_name
  ```
  - **Purpose:** Validates intake data, builds AFT JSON

- **`src/hcp_terraform.py`**
  ```python
  from github_api import GitHubApiError, ensure_git_branch
  ```
  - **Purpose:** Creates Git branches for HCP workspaces

- **`src/mcp_server.py`**
  ```python
  from github_api import (...)
  ```
  - **Purpose:** MCP server tools for AI orchestration

#### 2. **In Lambda Functions - AWS Execution (Serverless)**

**Copied to Lambda Layer:**
```
terraform/modules/lambda/lambda_functions/shared_layer/python/github_api.py
```

**Used by Lambda functions:**
- **`github_branch/handler.py`** - Creates Git branch
- **`github_commit/handler.py`** - Commits AFT JSON to GitHub
- **`validate_intake/handler.py`** - Validates intake data

---

## 🔄 Code Flow

### Source of Truth: `src/`

```
src/github_api.py           ← SOURCE OF TRUTH
src/hcp_terraform.py        ← SOURCE OF TRUTH
src/det_intake.py           ← SOURCE OF TRUTH
```

These files are the **single source of truth**. All changes should be made here.

### Lambda Layer: Copied During Build

```
src/github_api.py
    ↓ (copied during Terraform build)
terraform/modules/lambda/lambda_functions/shared_layer/python/github_api.py
    ↓ (packaged as Lambda layer)
AWS Lambda Layer
    ↓ (attached to Lambda functions)
Lambda Functions can import: from github_api import ...
```

**Terraform handles the copy automatically:**
```hcl
# terraform/modules/lambda/main.tf
data "archive_file" "lambda_layer" {
  source_dir  = "${path.module}/lambda_functions/shared_layer"
  output_path = "${path.module}/lambda_layer.zip"
}
```

---

## 🎯 Why This Organization?

### Single Source of Truth
- **`src/`** contains the original, authoritative code
- Lambda layer gets a **copy** during Terraform build
- Edit in `src/`, deploy via Terraform

### Code Reuse
Both the Slack bot and Lambda functions need the same GitHub operations:
- **Slack bot** uses it to list repos, validate input
- **Lambda functions** use it to create branches, commit files

### Independent Execution
- **Slack bot** runs locally on your machine
- **Lambda functions** run in AWS (serverless)
- Both need access to the same GitHub API code

---

## 📋 Function Reference

### `src/github_api.py` - All Functions

```python
# Repository Operations
list_org_repositories(owner: str, token: str) -> list[dict]
ensure_git_branch(owner: str, repo: str, branch: str, token: str, base_branch: str) -> None

# File Operations
put_repository_json_file(owner: str, repo: str, branch: str, file_path: str, 
                         data: dict, token: str, message: str) -> dict
build_github_intake_document(intake: dict) -> dict

# Utility
sanitize_git_branch_from_project_name(project_name: str) -> str

# Error Handling
class GitHubApiError(Exception)
```

### Usage in Slack Bot

```python
# In src/main_with_api_gateway.py
from github_api import list_org_repositories

# List repos for dropdown
repos = list_org_repositories(owner=GITHUB_OWNER, token=GITHUB_TOKEN)
```

### Usage in Lambda Functions

```python
# In lambda_functions/github_branch/handler.py
from github_api import ensure_git_branch

# Create branch
ensure_git_branch(owner, repo, branch_name, token, base_branch)
```

---

## 🔄 Update Process

### When You Change `src/github_api.py`

1. **Edit the source file:**
   ```bash
   vim src/github_api.py
   ```

2. **Deploy to AWS (Terraform copies it automatically):**
   ```bash
   cd terraform
   terraform apply
   ```

3. **Terraform will:**
   - Detect the source file changed
   - Copy it to Lambda layer
   - Package as `lambda_layer.zip`
   - Update Lambda layer in AWS
   - All Lambda functions get the new version

4. **Restart Slack bot (if running locally):**
   ```bash
   ./start_slack_bot.sh
   ```

---

## 🔍 Verifying the Files Are Identical

```bash
# Check if src/ and Lambda layer versions are the same
md5 src/github_api.py
md5 terraform/modules/lambda/lambda_functions/shared_layer/python/github_api.py

# Should show identical MD5 hashes
```

**Note:** Files are identical at deployment time. After you edit `src/github_api.py`, run `terraform apply` to sync.

---

## 🚨 Important Rules

### ✅ DO
- Edit code in `src/github_api.py`, `src/hcp_terraform.py`, `src/det_intake.py`
- Deploy via `terraform apply` to update Lambda functions
- Keep source files as the single source of truth

### ❌ DON'T
- Edit Lambda layer files directly (`terraform/modules/lambda/lambda_functions/shared_layer/python/*.py`)
- Manually copy files between `src/` and Lambda layer
- Commit Lambda layer `.zip` files to Git

### 🔄 Workflow
```
1. Edit src/github_api.py
2. Test locally (run Slack bot)
3. Run terraform apply (copies to Lambda layer + deploys)
4. Test in AWS
```

---

## 📊 File Dependencies

### Slack Bot Dependencies

```
main_with_api_gateway.py
    ├── github_api.py (list_org_repositories)
    ├── det_intake.py
    │   └── github_api.py (build_github_intake_document, sanitize_git_branch)
    ├── hcp_terraform.py
    │   └── github_api.py (ensure_git_branch)
    └── mcp_server.py
        └── github_api.py (all functions)
```

### Lambda Function Dependencies

```
Lambda Functions
    ├── validate_intake/handler.py
    │   └── det_intake.py (from Lambda layer)
    │       └── github_api.py (from Lambda layer)
    │
    ├── github_branch/handler.py
    │   └── github_api.py (from Lambda layer)
    │
    ├── github_commit/handler.py
    │   └── github_api.py (from Lambda layer)
    │
    └── hcp_workspace/handler.py
        └── hcp_terraform.py (from Lambda layer)
            └── github_api.py (from Lambda layer)
```

---

## 🎓 Summary

### Purpose of `src/github_api.py`

**Primary Purpose:** Source of truth for GitHub API integration

**Used By:**
1. **Slack Bot** (`src/main_with_api_gateway.py`) - Lists repos, validates intake
2. **Lambda Functions** (via shared layer) - Creates branches, commits files
3. **Other source files** (`det_intake.py`, `hcp_terraform.py`, `mcp_server.py`) - GitHub operations

**Key Point:** This file exists in **two places** but serves **one purpose**:
- `src/github_api.py` - Source of truth (edit here)
- `terraform/.../shared_layer/python/github_api.py` - Copy (deployed to AWS)

**Update Process:** Edit → Test → Deploy → Both environments have latest code

---

## 🔗 Related Documentation

- [LAMBDA_FUNCTIONS_MAPPING.md](LAMBDA_FUNCTIONS_MAPPING.md) - What each Lambda does
- [MODULAR_RESTRUCTURE.md](MODULAR_RESTRUCTURE.md) - Terraform module architecture
- [USER_JOURNEY.md](USER_JOURNEY.md) - Complete workflow
- [REORGANIZATION_COMPLETE.md](REORGANIZATION_COMPLETE.md) - Directory structure

---

**Key Takeaway:** `src/github_api.py` is referenced by **both** the Slack bot (direct import) and Lambda functions (via shared layer). It's the **single source of truth** for GitHub operations, copied to Lambda layer during Terraform deployment.
