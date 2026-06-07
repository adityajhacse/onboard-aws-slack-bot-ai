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

        intake = event.get("intake", {})
        project_name = intake.get("project_name", "")
        project_slug = intake.get("project_slug", "")

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

    except GitHubApiError as e:
        logger.error(f"GitHub API error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "branch_name": "",
            "branch_created": False,
            "error": f"GitHub API error: {str(e)}",
            "intake": event.get("intake", {}),
            "slack_channel": event.get("slack_channel"),
            "slack_user": event.get("slack_user"),
            "execution_id": event.get("execution_id"),
        }
    except Exception as e:
        logger.error(f"Branch creation error: {str(e)}", exc_info=True)
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
