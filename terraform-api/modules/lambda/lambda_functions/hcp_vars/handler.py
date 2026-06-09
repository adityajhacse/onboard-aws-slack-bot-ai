import json
import logging
import os
from typing import Any
from hcp_terraform import _set_workspace_env_vars, _hcp_config, HcpTerraformError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Configure environment variables for an HCP Terraform workspace.
    This function is called in parallel for each workspace.

    Input event (from Step Functions Map state):
    {
        "workspace_id": "ws-abc123",
        "workspace_name": "ems-dev",
        "environment": "Dev",
        ...
    }

    Output:
    {
        "workspace_id": "ws-abc123",
        "configured": true,
        "variables_set": ["TFC_AWS_PROVIDER_AUTH", "TFC_AWS_RUN_ROLE_ARN"],
        ...
    }
    """
    try:
        workspace = event.get("workspace") or event  # support both nested and flat input
        workspace_id = workspace.get("workspace_id", "")
        workspace_name = workspace.get("workspace_name", "")
        environment = workspace.get("environment", "")

        # Note: hcp_vars runs in parallel per workspace, not tracking overall step status here
        # The Step Functions will handle aggregating results

        # Get HCP config
        token, organization, base_url = _hcp_config()

        logger.info(f"Setting environment variables for workspace {workspace_id}")

        # Set workspace environment variables
        _set_workspace_env_vars(
            workspace_id=workspace_id,
            token=token,
            base_url=base_url,
        )

        logger.info(f"Variables configured for workspace {workspace_name}")

        return {
            "statusCode": 200,
            "workspace_id": workspace_id,
            "workspace_name": workspace_name,
            "environment": environment,
            "configured": True,
            "variables_set": ["TFC_AWS_PROVIDER_AUTH", "TFC_AWS_RUN_ROLE_ARN"],
        }

    except (HcpTerraformError, Exception) as e:
        logger.error(
            f"Variable configuration error for workspace {event.get('workspace_name')}: {str(e)}",
            exc_info=True,
        )

        try:
            from slack_notifier import notify_step_failure
            execution_id = event.get("execution_id") or ""
            if execution_id and ":execution:" in execution_id:
                execution_id = execution_id.split(":")[-1]
            notify_step_failure(
                step_name=f"Configure Workspace Variables ({event.get('workspace_name', '')})",
                execution_id=execution_id,
                slack_channel=event.get("slack_channel") or "",
                slack_user=event.get("slack_user") or "",
                error=str(e),
            )
        except Exception as notify_exc:
            logger.warning(f"Failed to send failure notification: {notify_exc}")

        return {
            "statusCode": 500,
            "workspace_id": event.get("workspace_id", ""),
            "workspace_name": event.get("workspace_name", ""),
            "environment": event.get("environment", ""),
            "configured": False,
            "error": str(e),
        }
