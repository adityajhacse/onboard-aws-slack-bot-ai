import json
import logging
import os
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Create GitHub branch for the intake request.

    Input event:
    {
        "intake": { validated intake data },
        "slack_channel": "C0123456789",
        "slack_user": "U0123456789",
        "execution_id": "arn:aws:states:..."
    }

    Output:
    {
        "branch_name": "ems-project",
        "branch_created": true,
        "intake": { ... },
        ...
    }
    """
    try:
        logger.info("Creating GitHub branch")

        from github_api import ensure_git_branch, sanitize_git_branch_from_project_name, GitHubApiError
        from dynamodb_helper import get_helper

        intake = event.get("intake", {})
        project_name = intake.get("project_name", "")
        project_slug = intake.get("project_slug", "")

        # Extract execution ID and update status
        execution_id = event.get("execution_id") or ""
        if execution_id and ":execution:" in execution_id:
            execution_id = execution_id.split(":")[-1]

        # Get DynamoDB helper once
        db = get_helper() if execution_id else None

        # Update status to RUNNING
        if db:
            try:
                db.update_step_status(execution_id, "CreateGitHubBranch", "RUNNING")
            except Exception as e:
                logger.warning(f"Failed to update status to RUNNING: {e}")

        # Get config from environment
        owner = os.environ.get("GITHUB_OWNER", "").strip()
        repo = os.environ.get("GITHUB_REPO", "").strip()
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        base_branch = os.environ.get("GITHUB_BASE_BRANCH", "main").strip()

        if not owner or not repo or not token:
            raise ValueError("Missing required GitHub configuration: GITHUB_OWNER, GITHUB_REPO, GITHUB_TOKEN")

        # Create branch name from project
        branch_name = sanitize_git_branch_from_project_name(project_name or project_slug or "intake")

        logger.info(f"Creating branch '{branch_name}' in {owner}/{repo} from {base_branch}")

        # Ensure branch exists
        ensure_git_branch(owner, repo, branch_name, base_branch, token)

        logger.info(f"Branch '{branch_name}' ready")

        # Update status to SUCCEEDED
        if db:
            try:
                db.update_step_status(
                    execution_id,
                    "CreateGitHubBranch",
                    "SUCCEEDED",
                    result={"branch_name": branch_name, "repository": f"{owner}/{repo}"}
                )
            except Exception as e:
                logger.warning(f"Failed to update status to SUCCEEDED: {e}")

        return {
            "statusCode": 200,
            "branch_name": branch_name,
            "branch_created": True,
            "repository": f"{owner}/{repo}",
            "intake": intake,
            "slack_channel": event.get("slack_channel"),
            "slack_user": event.get("slack_user"),
            "execution_id": event.get("execution_id"),
        }

    except (GitHubApiError, Exception) as e:
        logger.error(f"GitHub branch creation error: {str(e)}", exc_info=True)

        execution_id = event.get("execution_id") or ""
        if execution_id and ":execution:" in execution_id:
            execution_id = execution_id.split(":")[-1]

        try:
            from dynamodb_helper import get_helper
            db = get_helper()
            db.update_step_status(execution_id, "CreateGitHubBranch", "FAILED", error=str(e))
        except Exception as ex:
            logger.warning(f"Failed to update status to FAILED: {ex}")

        try:
            from slack_notifier import notify_step_failure
            notify_step_failure(
                step_name="Create GitHub Branch",
                execution_id=execution_id,
                slack_channel=event.get("slack_channel") or "",
                slack_user=event.get("slack_user") or "",
                project_name=(event.get("intake") or {}).get("project_name", ""),
                error=str(e),
            )
        except Exception as notify_exc:
            logger.warning(f"Failed to send failure notification: {notify_exc}")

        return {
            "statusCode": 500,
            "branch_name": "",
            "branch_created": False,
            "error": str(e),
            "intake": event.get("intake", {}),
            "slack_channel": event.get("slack_channel"),
            "slack_user": event.get("slack_user"),
            "execution_id": event.get("execution_id"),
        }
