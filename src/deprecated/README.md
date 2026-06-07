# Deprecated Code

This directory contains the old synchronous execution code that has been replaced by the Step Functions architecture.

## Deprecated Files

### main.OLD.py (formerly main.py)
- **Original purpose:** Synchronous Slack bot with inline GitHub and HCP Terraform operations
- **Deprecated date:** June 5, 2024
- **Replaced by:** `../main_with_api_gateway.py` (async execution via Step Functions)
- **Reason:** Moved to serverless Step Functions architecture for better retry logic, parallel execution, and status tracking

### Why This Was Replaced

The old `main.py` executed all operations synchronously in one process:
```python
# OLD synchronous code (deprecated)
@app.view("det_summary_modal")
def handle_det_summary_submit(ack, body, view, client):
    github_process(full_intake, user, channel_id, client)  # Blocking
    created = create_project_with_workspaces(...)          # Blocking
    # If any step failed, entire process failed
```

**Problems:**
- No retry logic per step
- Sequential execution (slow)
- All-or-nothing (one failure = total failure)
- No status tracking
- Slack timeouts on long operations

### New Architecture

The new `main_with_api_gateway.py` triggers Step Functions via API Gateway:
```python
# NEW async code
@app.view("det_summary_modal")
def handle_det_summary_submit(ack, body, view, client):
    result = api_client.trigger_onboarding(intake=full_intake, ...)
    # Returns immediately, workflow runs in background
    # Each step has retry logic
    # Status tracked in DynamoDB
    # Slack notification on completion
```

**Benefits:**
- ✅ Independent retry logic per step (2-3 retries each)
- ✅ Parallel workspace creation (3x faster)
- ✅ Complete status tracking in DynamoDB
- ✅ Automatic Slack notifications
- ✅ No Slack timeouts

## Migration Timeline

- **May 2024:** Original synchronous version created
- **June 5, 2024:** Step Functions architecture implemented
- **June 5, 2024:** Old version archived to this directory
- **Planned removal:** After 1 month of production stability (July 5, 2024)

## Do Not Use This Code

This code is kept for reference only. All new deployments should use:
- **Slack Bot:** `src/main_with_api_gateway.py`
- **Infrastructure:** Terraform in `terraform/` directory
- **Lambda Functions:** `lambda_functions/` directory

## Questions?

See documentation:
- `MIGRATION_CLEANUP_GUIDE.md` - Complete migration guide
- `USER_JOURNEY.md` - How new architecture works
- `DEPLOYMENT.md` - Deployment instructions
