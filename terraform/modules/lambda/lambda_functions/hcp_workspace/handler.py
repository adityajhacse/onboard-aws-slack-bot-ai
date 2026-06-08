import json
import logging
import os
from typing import Any
from hcp_terraform import (
    _create_workspace,
    _resolve_workspace_name,
    _hcp_config,
    HcpTerraformError
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Create HCP Terraform workspace for a single environment.
    This function is called in parallel for each environment.

    Input event (from Step Functions Map state):
    {
        "environment": "Dev",
        "project_id": "prj-abc123",
        "project_slug": "ems",
        "terraform_repo": "my-org/terraform-ems",
        "workspace_names": {"Dev": "ems-dev", "QA": "ems-qa"},
        ...
    }

    Output:
    {
        "workspace_id": "ws-abc123",
        "workspace_name": "ems-dev",
        "environment": "Dev",
        ...
    }
    """
    try:
        from dynamodb_helper import get_helper

        environment = event.get("environment", "")
        project_id = event.get("project_id", "")
        project_slug = event.get("project_slug", "")
        terraform_repo = event.get("terraform_repo", "")
        workspace_names_map = event.get("workspace_names", {})

        # Extract execution ID for status tracking
        execution_id = event.get("execution_id") or ""
        if execution_id and ":execution:" in execution_id:
            execution_id = execution_id.split(":")[-1]

        # Get DynamoDB helper once
        db = get_helper() if execution_id else None

        # Get HCP config
        token, organization, base_url = _hcp_config()

        # Determine workspace name
        workspace_name = _resolve_workspace_name(
            project_slug=project_slug,
            environment=environment,
            workspace_names=workspace_names_map,
        )

        environment_slug = environment.strip().lower()

        logger.info(f"Creating workspace '{workspace_name}' for {environment} in project {project_id}")

        # Create workspace
        workspace = _create_workspace(
            workspace_name=workspace_name,
            environment_slug=environment_slug,
            project_id=project_id,
            terraform_repo=terraform_repo,
            token=token,
            organization=organization,
            base_url=base_url,
        )

        workspace_id = workspace["id"]
        workspace_display_name = workspace["name"]

        logger.info(f"Workspace created: {workspace_display_name} (ID: {workspace_id})")

        # Update workspace result in DynamoDB
        if db:
            try:
                db.add_workspace_result(
                    execution_id=execution_id,
                    environment=environment,
                    workspace_id=workspace_id,
                    workspace_name=workspace_display_name,
                    success=True
                )
            except Exception as e:
                logger.warning(f"Failed to record workspace result: {e}")

        return {
            "statusCode": 200,
            "workspace_id": workspace_id,
            "workspace_name": workspace_display_name,
            "environment": environment,
            "project_id": project_id,
        }

    except HcpTerraformError as e:
        logger.error(f"HCP Terraform error for {event.get('environment')}: {str(e)}", exc_info=True)

        # Record workspace failure
        try:
            execution_id = event.get("execution_id") or ""
            if execution_id and ":execution:" in execution_id:
                execution_id = execution_id.split(":")[-1]
            if execution_id:
                from dynamodb_helper import get_helper
                db = get_helper()
                db.add_workspace_result(
                    execution_id=execution_id,
                    environment=event.get("environment", ""),
                    workspace_id="",
                    workspace_name="",
                    success=False,
                    error=str(e)
                )
        except Exception as ex:
            logger.warning(f"Failed to record workspace failure: {ex}")

        return {
            "statusCode": 500,
            "workspace_id": "",
            "workspace_name": "",
            "environment": event.get("environment", ""),
            "error": f"HCP Terraform error: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Workspace creation error for {event.get('environment')}: {str(e)}", exc_info=True)

        # Record workspace failure
        try:
            execution_id = event.get("execution_id") or ""
            if execution_id and ":execution:" in execution_id:
                execution_id = execution_id.split(":")[-1]
            if execution_id:
                from dynamodb_helper import get_helper
                db = get_helper()
                db.add_workspace_result(
                    execution_id=execution_id,
                    environment=event.get("environment", ""),
                    workspace_id="",
                    workspace_name="",
                    success=False,
                    error=str(e)
                )
        except Exception as ex:
            logger.warning(f"Failed to record workspace failure: {ex}")

        return {
            "statusCode": 500,
            "workspace_id": "",
            "workspace_name": "",
            "environment": event.get("environment", ""),
            "error": str(e),
        }
