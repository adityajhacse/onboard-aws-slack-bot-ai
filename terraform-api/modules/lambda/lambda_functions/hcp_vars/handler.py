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
        workspace_id = event.get("workspace_id", "")
        workspace_name = event.get("workspace_name", "")
        environment = event.get("environment", "")

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

    except HcpTerraformError as e:
        logger.error(
            f"HCP Terraform error for workspace {event.get('workspace_name')}: {str(e)}",
            exc_info=True
        )
        return {
            "statusCode": 500,
            "workspace_id": event.get("workspace_id", ""),
            "workspace_name": event.get("workspace_name", ""),
            "environment": event.get("environment", ""),
            "configured": False,
            "error": f"HCP Terraform error: {str(e)}",
        }
    except Exception as e:
        logger.error(
            f"Variable configuration error for workspace {event.get('workspace_name')}: {str(e)}",
            exc_info=True
        )
        return {
            "statusCode": 500,
            "workspace_id": event.get("workspace_id", ""),
            "workspace_name": event.get("workspace_name", ""),
            "environment": event.get("environment", ""),
            "configured": False,
            "error": str(e),
        }
