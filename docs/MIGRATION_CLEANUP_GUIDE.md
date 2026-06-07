# Migration & Cleanup Guide

## What's Redundant After Step Functions Migration

### 🗑️ Files That Are Now Redundant

#### 1. **src/main.py** (Old Synchronous Version)
- **Status:** Redundant if using `main_with_api_gateway.py`
- **Action:** 
  - Option A: Delete (recommended after testing)
  - Option B: Rename to `main.OLD.py` (keep as reference)
  - Option C: Keep for gradual migration

**Reason:** The old `handle_det_summary_submit()` function does synchronous execution:
```python
# OLD synchronous code (now redundant)
github_process(full_intake, user, channel_id, client)
created = create_project_with_workspaces(...)
```

This is replaced by:
```python
# NEW async code in main_with_api_gateway.py
result = api_client.trigger_onboarding(intake=full_intake, ...)
```

---

### ✅ Files That MUST Be Kept

#### 1. **Core Modules (Source of Truth)**

These are the SOURCE files that get copied to Lambda layer:

- ✅ **src/github_api.py** - GitHub API operations (copied to Lambda layer)
- ✅ **src/hcp_terraform.py** - HCP Terraform operations (copied to Lambda layer)
- ✅ **src/det_intake.py** - Validation & normalization (copied to Lambda layer)

**Keep these!** The Lambda layer copies from here:
```bash
cp src/github_api.py lambda_functions/shared_layer/python/
cp src/hcp_terraform.py lambda_functions/shared_layer/python/
cp src/det_intake.py lambda_functions/shared_layer/python/
```

#### 2. **Slack Bot Files (Still Needed)**

- ✅ **src/main_with_api_gateway.py** - NEW async Slack bot
- ✅ **src/api_gateway_client.py** - API Gateway client
- ✅ **src/modal_lib.py** - Slack modal builder
- ✅ **src/session_store.py** - Session management
- ✅ **src/ai_orchestrator.py** - AI chat orchestrator
- ✅ **src/mcp_client.py** - MCP client
- ✅ **src/mcp_server.py** - MCP server

---

## 📁 Recommended File Structure After Cleanup

### Current Structure:
```
src/
├── main.py                      ⚠️ OLD (redundant)
├── main_with_api_gateway.py     ✅ NEW (keep)
├── api_gateway_client.py        ✅ NEW (keep)
├── github_api.py                ✅ SOURCE (keep - copied to Lambda)
├── hcp_terraform.py             ✅ SOURCE (keep - copied to Lambda)
├── det_intake.py                ✅ SOURCE (keep - copied to Lambda)
├── modal_lib.py                 ✅ NEEDED (keep)
├── session_store.py             ✅ NEEDED (keep)
├── ai_orchestrator.py           ✅ NEEDED (keep)
├── mcp_client.py                ✅ NEEDED (keep)
└── mcp_server.py                ✅ NEEDED (keep)
```

### Recommended After Cleanup:
```
src/
├── main_with_api_gateway.py     ✅ Primary Slack bot (async)
├── api_gateway_client.py        ✅ API Gateway client
├── github_api.py                ✅ SOURCE - copied to Lambda layer
├── hcp_terraform.py             ✅ SOURCE - copied to Lambda layer
├── det_intake.py                ✅ SOURCE - copied to Lambda layer
├── modal_lib.py                 ✅ Slack modal builder
├── session_store.py             ✅ Session management
├── ai_orchestrator.py           ✅ AI chat
├── mcp_client.py                ✅ MCP integration
├── mcp_server.py                ✅ MCP server
└── deprecated/
    └── main.OLD.py              📦 Old sync version (archived)
```

---

## 🔄 Migration Strategy

### Phase 1: Test New System (Current)
Keep both `main.py` and `main_with_api_gateway.py`:
- Test new async version thoroughly
- Keep old version as fallback
- Compare results

### Phase 2: Run in Parallel (Recommended)
```bash
# Terminal 1: Run new async version
cd src
python main_with_api_gateway.py

# Terminal 2: Monitor executions
aws logs tail /aws/states/det-onboarding-prod-onboarding --follow
```

### Phase 3: Deprecate Old Version
After 1-2 weeks of successful production use:

```bash
# Archive old version
mkdir -p src/deprecated
mv src/main.py src/deprecated/main.OLD.py

# Update README
echo "Note: main.py moved to deprecated/. Use main_with_api_gateway.py" >> src/README.md

# Update documentation
echo "Old synchronous execution deprecated. Use Step Functions architecture." >> CHANGELOG.md
```

### Phase 4: Full Cleanup (Optional)
After 1 month in production without issues:

```bash
# Remove archived old version
rm -rf src/deprecated/

# Update git
git rm src/deprecated/main.OLD.py
git commit -m "Remove deprecated synchronous execution code"
```

---

## 🎯 Cleanup Commands

### Option A: Archive Old Code (Recommended)

```bash
# Create archive directory
mkdir -p src/deprecated

# Move old synchronous version
mv src/main.py src/deprecated/main.OLD.py

# Rename new version to be primary
# (Optional - or just update your startup command)
# mv src/main_with_api_gateway.py src/main.py
# mv src/api_gateway_client.py stays as is

# Create note
cat > src/deprecated/README.md << 'EOF'
# Deprecated Code

This directory contains the old synchronous execution code.

**Deprecated:** src/main.py (synchronous execution)
**Replaced by:** src/main_with_api_gateway.py (async with Step Functions)

**Deprecated date:** 2024-06-05
**Removal planned:** After 1 month of production stability

Do not use code in this directory for new work.
EOF
```

### Option B: Complete Removal (After Testing)

```bash
# Remove old synchronous version completely
rm src/main.py

# Update any references
grep -r "from main import" src/
# (Update any imports if needed)

# Commit
git add -A
git commit -m "Remove deprecated synchronous execution code"
```

---

## 🔍 What Each File Does Now

### Lambda Functions (NEW Execution)
```
lambda_functions/
├── validate_intake/        → Validates form
├── github_branch/          → Creates branch
├── github_commit/          → Creates AFT JSON & commits
├── hcp_project/            → Creates HCP project
├── hcp_workspace/          → Creates workspaces
├── hcp_vars/               → Configures variables
├── status_tracker/         → Tracks in DynamoDB
├── completion_notifier/    → Sends Slack messages
└── shared_layer/python/    → COPY of src/ modules
    ├── github_api.py       ← COPIED from src/
    ├── hcp_terraform.py    ← COPIED from src/
    ├── det_intake.py       ← COPIED from src/
    └── dynamodb_helper.py  ← NEW module
```

### Source Files (KEEP as source of truth)
```
src/
├── github_api.py           → SOURCE (copied to Lambda layer)
├── hcp_terraform.py        → SOURCE (copied to Lambda layer)
├── det_intake.py           → SOURCE (copied to Lambda layer)
```

### Slack Bot (KEEP for user interaction)
```
src/
├── main_with_api_gateway.py → NEW async Slack bot
├── api_gateway_client.py    → Calls API Gateway
├── modal_lib.py             → Builds Slack modals
├── session_store.py         → Manages sessions
├── ai_orchestrator.py       → AI chat features
```

---

## 📝 Update Startup Instructions

### Old Instructions (Deprecated):
```bash
cd src && python main.py
```

### New Instructions:
```bash
# Set API Gateway endpoint
export API_GATEWAY_ENDPOINT=$(cd terraform && terraform output -raw api_gateway_url)

# Run new async Slack bot
cd src && python main_with_api_gateway.py
```

Or create a startup script:

```bash
# File: start_slack_bot.sh
#!/bin/bash

# Get API Gateway URL from Terraform
cd terraform
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null)
cd ..

if [ -z "$API_URL" ]; then
    echo "Error: Could not get API Gateway URL from Terraform"
    echo "Run: cd terraform && terraform output api_gateway_url"
    exit 1
fi

# Export for the app
export API_GATEWAY_ENDPOINT="$API_URL"

# Start Slack bot
cd src
echo "Starting Slack bot with API Gateway: $API_URL"
python main_with_api_gateway.py
```

---

## ⚠️ Important Notes

### DO NOT Remove These Files:

1. **src/github_api.py** - Source of truth, copied to Lambda layer
2. **src/hcp_terraform.py** - Source of truth, copied to Lambda layer
3. **src/det_intake.py** - Source of truth, copied to Lambda layer
4. **src/modal_lib.py** - Still used by Slack bot
5. **src/session_store.py** - Still used by Slack bot
6. **src/ai_orchestrator.py** - Still used for AI chat

### Can Remove (After Testing):

1. **src/main.py** - Old synchronous execution (replaced by main_with_api_gateway.py)
2. Old function: `handle_det_summary_submit()` that calls `github_process()` and `create_project_with_workspaces()`

---

## 🧪 Testing Before Removal

Before removing old code, verify:

```bash
# 1. Test new system
cd src
python main_with_api_gateway.py

# In Slack:
# /aws-det-poc → Fill form → Submit

# 2. Check execution completed
aws dynamodb scan --table-name det-onboarding-prod-executions --limit 1

# 3. Verify GitHub commit
# Visit: https://github.com/adityajhacse/test

# 4. Verify HCP project
# Visit: https://app.terraform.io/app/adityajhacse

# 5. Check Slack notification received
# Look for "🎉 Onboarding completed" message
```

If all tests pass for 1-2 weeks → Safe to remove `main.py`

---

## 📊 Redundancy Summary

| File | Status | Action |
|------|--------|--------|
| `src/main.py` | ⚠️ Redundant | Archive or remove after testing |
| `src/main_with_api_gateway.py` | ✅ Active | Keep - primary Slack bot |
| `src/api_gateway_client.py` | ✅ Active | Keep - API client |
| `src/github_api.py` | ✅ Source | **Keep - copied to Lambda layer** |
| `src/hcp_terraform.py` | ✅ Source | **Keep - copied to Lambda layer** |
| `src/det_intake.py` | ✅ Source | **Keep - copied to Lambda layer** |
| `src/modal_lib.py` | ✅ Active | Keep - Slack modals |
| `src/session_store.py` | ✅ Active | Keep - sessions |
| `src/ai_orchestrator.py` | ✅ Active | Keep - AI features |

---

## 🎯 Conclusion

**Redundant:**
- ❌ `src/main.py` - Old synchronous execution logic

**Must Keep:**
- ✅ Core modules (`github_api.py`, `hcp_terraform.py`, `det_intake.py`) - Source files copied to Lambda layer
- ✅ Slack bot files (`main_with_api_gateway.py`, `modal_lib.py`, etc.) - Still needed for user interaction

**Recommendation:**
1. Archive `main.py` to `deprecated/` folder
2. Use `main_with_api_gateway.py` as primary
3. Keep all core modules as source of truth
4. Remove archived file after 1 month of stable production
