import json
import logging
import os
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def check_duplicate_project(db, project_name: str) -> dict[str, Any] | None:
    """
    Check if a project with the same name already has an onboarding request.

    Returns the existing request if found, None otherwise.
    Only considers SUCCEEDED or RUNNING requests (ignores FAILED).
    """
    try:
        # Query DynamoDB by project name using GSI
        response = db.table.query(
            IndexName='project-name-index',
            KeyConditionExpression='project_name = :project_name',
            ExpressionAttributeValues={':project_name': project_name},
            ScanIndexForward=False,  # Most recent first
            Limit=10,  # Check last 10 requests for this project
        )

        items = response.get('Items', [])

        if not items:
            logger.info(f"No existing requests found for project: {project_name}")
            return None

        # Check for SUCCEEDED or RUNNING requests
        for item in items:
            status = item.get('status', '')
            if status in ('SUCCEEDED', 'RUNNING'):
                logger.warning(
                    f"Found duplicate request for project '{project_name}': "
                    f"SR ID={item.get('service_request_id')}, Status={status}"
                )
                return item

        logger.info(f"Found {len(items)} requests for project '{project_name}' but all are FAILED")
        return None

    except Exception as e:
        logger.error(f"Error checking for duplicate project: {e}", exc_info=True)
        # Don't block onboarding if duplicate check fails
        return None


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
        from dynamodb_helper import get_helper

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

        project_name = validation_result['intake'].get('project_name', '')
        logger.info(f"Validation successful for project: {project_name}")

        # Check for duplicate project name in existing requests
        db = get_helper()
        duplicate = check_duplicate_project(db, project_name)

        if duplicate:
            error_msg = (
                f"Onboarding request already exists for project '{project_name}'. "
                f"Service Request ID: {duplicate.get('service_request_id', 'N/A')}, "
                f"Status: {duplicate.get('status', 'UNKNOWN')}, "
                f"Created: {duplicate.get('created_at', 'N/A')}"
            )
            logger.warning(error_msg)
            return {
                "statusCode": 400,
                "valid": False,
                "intake": validation_result["intake"],
                "missing_fields": [],
                "errors": [error_msg],
                "duplicate_request": {
                    "service_request_id": duplicate.get('service_request_id'),
                    "status": duplicate.get('status'),
                    "created_at": duplicate.get('created_at'),
                },
                "slack_channel": slack_channel,
                "slack_user": slack_user,
                "execution_id": execution_id,
            }

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
