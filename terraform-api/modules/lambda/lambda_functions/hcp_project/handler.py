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

        from dynamodb_helper import get_helper

        intake = event.get("intake", {})
        project_name = intake.get("project_upper", "") or intake.get("project_name", "")

        # Extract execution ID and update status
        execution_id = event.get("execution_id") or ""
        if execution_id and ":execution:" in execution_id:
            execution_id = execution_id.split(":")[-1]

        # Get DynamoDB helper once
        db = get_helper() if execution_id else None

        # Update status to RUNNING
        if db:
            try:
                db.update_step_status(execution_id, "CreateHCPProject", "RUNNING")
            except Exception as e:
                logger.warning(f"Failed to update status to RUNNING: {e}")

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

        # Update status to SUCCEEDED
        if db:
            try:
                db.update_step_status(
                    execution_id,
                    "CreateHCPProject",
                    "SUCCEEDED",
                    result={"project_id": project_id, "project_name": project_display_name}
                )
            except Exception as e:
                logger.warning(f"Failed to update status to SUCCEEDED: {e}")

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

        # Update status to FAILED
        try:
            execution_id = event.get("execution_id") or ""
            if execution_id and ":execution:" in execution_id:
                execution_id = execution_id.split(":")[-1]
            if execution_id:
                from dynamodb_helper import get_helper
                db = get_helper()
                db.update_step_status(execution_id, "CreateHCPProject", "FAILED", error=str(e))
        except Exception as ex:
            logger.warning(f"Failed to update status to FAILED: {ex}")

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

        # Update status to FAILED
        try:
            execution_id = event.get("execution_id") or ""
            if execution_id and ":execution:" in execution_id:
                execution_id = execution_id.split(":")[-1]
            if execution_id:
                from dynamodb_helper import get_helper
                db = get_helper()
                db.update_step_status(execution_id, "CreateHCPProject", "FAILED", error=str(e))
        except Exception as ex:
            logger.warning(f"Failed to update status to FAILED: {ex}")

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
