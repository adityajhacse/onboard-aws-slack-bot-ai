import json
import logging
import os
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Validate and normalize intake data from Slack form submission.

    Input event:
    {
        "intake": {
            "project_name": "EMS",
            "terraform_repo": "my-org/terraform-ems",
            "team_channel": "C0123456789",
            "environments": ["Dev", "QA"],
            "regions": ["us-east-1"],
            "vpc_model": "Small",
            "service_name": "EMS API",
            "business_justification": "...",
            "team_dl": "team@example.com"
        },
        "slack_channel": "C0123456789",
        "slack_user": "U0123456789",
        "execution_id": "arn:aws:states:..."
    }

    Output:
    {
        "valid": true,
        "intake": { normalized intake data },
        "missing_fields": [],
        "errors": []
    }
    """
    try:
        logger.info(f"Validating intake data: {json.dumps(event, default=str)}")

        # Import shared layer modules
        from det_intake import validate_intake, normalize_intake

        intake_data = event.get("intake", {})
        slack_channel = event.get("slack_channel")
        slack_user = event.get("slack_user")
        execution_id = event.get("execution_id")

        # Validate intake
        validation_result = validate_intake(intake_data)

        if not validation_result["valid"]:
            logger.warning(
                f"Validation failed - missing: {validation_result['missing_fields']}, "
                f"errors: {validation_result['errors']}"
            )
            return {
                "statusCode": 400,
                "valid": False,
                "intake": validation_result["intake"],
                "missing_fields": validation_result["missing_fields"],
                "errors": validation_result["errors"],
                "slack_channel": slack_channel,
                "slack_user": slack_user,
                "execution_id": execution_id,
            }

        logger.info(f"Validation successful for project: {validation_result['intake'].get('project_name')}")

        return {
            "statusCode": 200,
            "valid": True,
            "intake": validation_result["intake"],
            "missing_fields": [],
            "errors": [],
            "slack_channel": slack_channel,
            "slack_user": slack_user,
            "execution_id": execution_id,
        }

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "valid": False,
            "intake": event.get("intake", {}),
            "missing_fields": [],
            "errors": [f"Validation service error: {str(e)}"],
            "slack_channel": event.get("slack_channel"),
            "slack_user": event.get("slack_user"),
            "execution_id": event.get("execution_id"),
        }
