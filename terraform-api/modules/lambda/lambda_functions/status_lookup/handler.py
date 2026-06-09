"""
Status Lookup Lambda Function
Handles status queries by Service Request ID via API Gateway.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle status lookup requests via API Gateway.

    API Gateway Event:
    {
        "httpMethod": "GET",
        "queryStringParameters": {
            "service_request_id": "SR-20260608-1234"
        }
    }

    Or POST:
    {
        "httpMethod": "POST",
        "body": "{\"service_request_id\": \"SR-20260608-1234\"}"
    }

    Response:
    {
        "statusCode": 200,
        "body": "{...execution data...}"
    }
    """
    try:
        from dynamodb_helper import get_helper

        # Extract Service Request ID from request
        service_request_id = None

        if event.get('httpMethod') == 'GET':
            params = event.get('queryStringParameters') or {}
            service_request_id = params.get('service_request_id')
        elif event.get('httpMethod') == 'POST':
            body = json.loads(event.get('body', '{}'))
            service_request_id = body.get('service_request_id')

        if not service_request_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': 'Missing service_request_id parameter',
                    'message': 'Please provide service_request_id in query string or body',
                }),
            }

        logger.info(f"Looking up status for {service_request_id}")

        # Query DynamoDB
        db = get_helper()
        logger.info(f"DynamoDB table: {db.table_name}")

        execution = db.get_execution_by_service_request_id(service_request_id)

        logger.info(f"Query result: {execution is not None}")
        if execution:
            logger.info(f"Found execution: {execution.get('execution_id')}")

        if not execution:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': 'Not found',
                    'message': f'No execution found for Service Request ID: {service_request_id}',
                    'service_request_id': service_request_id,
                }),
            }

        # Format response
        response_data = format_execution_for_api(execution)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps(response_data, default=str),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Invalid JSON in request body'}),
        }
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e),
            }),
        }


def format_execution_for_api(execution: dict[str, Any]) -> dict[str, Any]:
    """
    Format execution record for API response.

    Args:
        execution: Raw DynamoDB execution record

    Returns:
        Formatted response data
    """
    service_request_id = execution.get('service_request_id', 'N/A')
    project_name = execution.get('project_name', 'Unknown')
    status = execution.get('status', 'UNKNOWN')
    created_at = execution.get('created_at', '')
    completed_at = execution.get('completed_at')
    error_message = execution.get('error_message')

    # Calculate time information
    time_info = calculate_time_info(created_at, completed_at)

    # Extract step statuses
    steps = {
        'validate_intake': execution.get('step_validate_intake', 'UNKNOWN'),
        'github_branch': execution.get('step_github_branch', 'UNKNOWN'),
        'github_commit': execution.get('step_github_commit', 'UNKNOWN'),
        'hcp_project': execution.get('step_hcp_project', 'UNKNOWN'),
        'workspaces': execution.get('step_workspaces', 'UNKNOWN'),
        'variables': execution.get('step_variables', 'UNKNOWN'),
    }

    # Build response
    response = {
        'service_request_id': service_request_id,
        'project_name': project_name,
        'status': status,
        'created_at': created_at,
        'completed_at': completed_at,
        'time_elapsed_seconds': time_info['elapsed_seconds'],
        'time_display': time_info['display'],
        'steps': steps,
        'current_step': execution.get('current_step'),
    }

    if error_message:
        response['error_message'] = error_message

    # Include results if completed
    if status == 'SUCCEEDED' and execution.get('results'):
        response['results'] = execution.get('results')

    return response


def calculate_time_info(created_at: str, completed_at: Optional[str]) -> dict[str, Any]:
    """Calculate time elapsed information."""
    if not created_at:
        return {
            'elapsed_seconds': None,
            'display': 'Unknown',
        }

    try:
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        if completed_at:
            completed = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            elapsed = completed - created
            seconds = int(elapsed.total_seconds())
            return {
                'elapsed_seconds': seconds,
                'display': f"Completed in {seconds} seconds",
            }
        else:
            now = datetime.now(timezone.utc)
            elapsed = now - created
            seconds = int(elapsed.total_seconds())
            minutes = seconds // 60
            secs = seconds % 60

            if minutes > 0:
                display = f"Running for {minutes}m {secs}s"
            else:
                display = f"Running for {secs}s"

            return {
                'elapsed_seconds': seconds,
                'display': display,
            }
    except Exception as e:
        logger.warning(f"Error calculating time: {e}")
        return {
            'elapsed_seconds': None,
            'display': 'Unknown',
        }
