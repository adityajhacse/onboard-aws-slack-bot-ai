import json
import logging
import os
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Commit intake document to GitHub.

    Input event:
    {
        "intake": { validated intake data },
        "branch_name": "ems-project",
        "slack_channel": "C0123456789",
        "slack_user": "U0123456789",
        "execution_id": "arn:aws:states:..."
    }

    Output:
    {
        "commit_sha": "abc123...",
        "file_url": "https://github.com/...",
        "file_path": "requests/ems-dev.json",
        ...
    }
    """
    try:
        logger.info("Committing to GitHub")

        from github_api import (
            put_repository_json_file,
            build_github_intake_document,
            GitHubApiError
        )
        from dynamodb_helper import get_helper

        intake = event.get("intake", {})
        branch_name = event.get("branch_name", "")
        slack_user_data = {"id": event.get("slack_user", "")}

        # Extract execution ID and update status
        execution_id = event.get("execution_id") or ""
        if execution_id and ":execution:" in execution_id:
            execution_id = execution_id.split(":")[-1]

        # Get DynamoDB helper once
        db = get_helper() if execution_id else None

        # Update status to RUNNING
        if db:
            try:
                db.update_step_status(execution_id, "CommitToGitHub", "RUNNING")
            except Exception as e:
                logger.warning(f"Failed to update status to RUNNING: {e}")

        if not branch_name:
            raise ValueError("Missing branch_name from previous step")

        # Get config from environment
        owner = os.environ.get("GITHUB_OWNER", "").strip()
        repo = os.environ.get("GITHUB_REPO", "").strip()
        token = os.environ.get("GITHUB_TOKEN", "").strip()

        if not owner or not repo or not token:
            raise ValueError("Missing required GitHub configuration")

        # Build intake document
        default_path, payload = build_github_intake_document(intake, slack_user_data)
        file_path = os.environ.get("GITHUB_FILE_PATH", "").strip() or default_path
        request_id = payload.get("request_id", "")

        logger.info(f"Committing {file_path} to {owner}/{repo}:{branch_name}")

        # Commit to GitHub
        result = put_repository_json_file(
            owner=owner,
            repo=repo,
            path=file_path,
            data=payload,
            commit_message=f"DET intake {request_id}",
            token=token,
            branch=branch_name,
        )

        commit_sha = (result.get("commit") or {}).get("sha", "")
        file_url = (result.get("content") or {}).get("html_url", "")

        logger.info(f"Committed successfully: {file_url}")

        # Update status to SUCCEEDED
        if db:
            try:
                db.update_step_status(
                    execution_id,
                    "CommitToGitHub",
                    "SUCCEEDED",
                    result={"commit_sha": commit_sha, "file_url": file_url, "file_path": file_path}
                )
            except Exception as e:
                logger.warning(f"Failed to update status to SUCCEEDED: {e}")

        return {
            "statusCode": 200,
            "commit_sha": commit_sha,
            "file_url": file_url,
            "file_path": file_path,
            "request_id": request_id,
            "branch_name": branch_name,
            "intake": intake,
            "slack_channel": event.get("slack_channel"),
            "slack_user": event.get("slack_user"),
            "execution_id": event.get("execution_id"),
        }

    except GitHubApiError as e:
        logger.error(f"GitHub API error: {str(e)}", exc_info=True)

        # Update status to FAILED
        try:
            execution_id = event.get("execution_id") or ""
            if execution_id and ":execution:" in execution_id:
                execution_id = execution_id.split(":")[-1]
            if execution_id:
                from dynamodb_helper import get_helper
                db = get_helper()
                db.update_step_status(execution_id, "CommitToGitHub", "FAILED", error=str(e))
        except Exception as ex:
            logger.warning(f"Failed to update status to FAILED: {ex}")

        return {
            "statusCode": 500,
            "commit_sha": "",
            "file_url": "",
            "error": f"GitHub commit error: {str(e)}",
            "intake": event.get("intake", {}),
            "slack_channel": event.get("slack_channel"),
            "slack_user": event.get("slack_user"),
            "execution_id": event.get("execution_id"),
        }
    except Exception as e:
        logger.error(f"Commit error: {str(e)}", exc_info=True)

        # Update status to FAILED
        try:
            execution_id = event.get("execution_id") or ""
            if execution_id and ":execution:" in execution_id:
                execution_id = execution_id.split(":")[-1]
            if execution_id:
                from dynamodb_helper import get_helper
                db = get_helper()
                db.update_step_status(execution_id, "CommitToGitHub", "FAILED", error=str(e))
        except Exception as ex:
            logger.warning(f"Failed to update status to FAILED: {ex}")

        return {
            "statusCode": 500,
            "commit_sha": "",
            "file_url": "",
            "error": str(e),
            "intake": event.get("intake", {}),
            "slack_channel": event.get("slack_channel"),
            "slack_user": event.get("slack_user"),
            "execution_id": event.get("execution_id"),
        }
