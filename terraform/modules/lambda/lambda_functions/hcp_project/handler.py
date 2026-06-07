import json
import logging
import os
from typing import Any
from hcp_terraform import _create_project, _hcp_config, HcpTerraformError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Create HCP Terraform project.

    Input event:
    {
        "intake": { validated intake data },
        ...
    }

    Output:
    {
        "project_id": "prj-abc123",
        "project_name": "EMS",
        ...
    }
    """
    try:
        logger.info("Creating HCP Terraform project")

        intake = event.get("intake", {})
        project_name = intake.get("project_upper", "") or intake.get("project_name", "")

        if not project_name:
            raise ValueError("Missing project_name in intake data")

        # Get HCP config
        token, organization, base_url = _hcp_config()

        logger.info(f"Creating project '{project_name}' in HCP org '{organization}'")

        # Create project
        project = _create_project(
            project_name=project_name,
            token=token,
            organization=organization,
            base_url=base_url,
        )

        project_id = project["id"]
        project_display_name = project["name"]

        logger.info(f"Project created: {project_display_name} (ID: {project_id})")

        return {
            "statusCode": 200,
            "project_id": project_id,
            "project_name": project_display_name,
            "intake": intake,
            "slack_channel": event.get("slack_channel"),
            "slack_user": event.get("slack_user"),
            "execution_id": event.get("execution_id"),
            "file_url": event.get("file_url"),
            "branch_name": event.get("branch_name"),
        }

    except HcpTerraformError as e:
        logger.error(f"HCP Terraform error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "project_id": "",
            "project_name": "",
            "error": f"HCP Terraform error: {str(e)}",
            "intake": event.get("intake", {}),
            "slack_channel": event.get("slack_channel"),
            "slack_user": event.get("slack_user"),
            "execution_id": event.get("execution_id"),
        }
    except Exception as e:
        logger.error(f"Project creation error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "project_id": "",
            "project_name": "",
            "error": str(e),
            "intake": event.get("intake", {}),
            "slack_channel": event.get("slack_channel"),
            "slack_user": event.get("slack_user"),
            "execution_id": event.get("execution_id"),
        }
