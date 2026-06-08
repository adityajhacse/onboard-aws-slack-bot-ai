import json
import logging
import os
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Track execution status in DynamoDB.
    This Lambda is called by Step Functions to update progress.

    Input event:
    {
        "execution_id": "arn:aws:states:...",
        "action": "start" | "step_update" | "complete" | "fail",
        "step_name": "ValidateIntake",
        "step_status": "RUNNING" | "SUCCEEDED" | "FAILED",
        "result": { optional result data },
        "error": "optional error message",
        "intake": { intake data for start action },
        "slack_channel": "C0123456789",
        "slack_user": "U0123456789"
    }

    Output:
    {
        "statusCode": 200,
        "tracked": true,
        "execution_id": "...",
        ...
    }
    """
    try:
        from dynamodb_helper import get_helper

        db = get_helper()

        action = event.get('action', '')
        execution_id = event.get('execution_id', '')

        # Extract execution ID from ARN if needed
        if ':execution:' in execution_id:
            execution_id = execution_id.split(':')[-1]

        logger.info(f"Tracking status - Action: {action}, Execution: {execution_id}")

        if action == 'start':
            # Create initial execution record
            intake = event.get('intake', {})
            slack_channel = event.get('slack_channel', '')
            slack_user = event.get('slack_user', '')

            record = db.create_execution_record(
                execution_id=execution_id,
                intake=intake,
                slack_channel=slack_channel,
                slack_user=slack_user,
            )

            return {
                'statusCode': 200,
                'tracked': True,
                'execution_id': execution_id,
                'service_request_id': record.get('service_request_id'),
                'action': 'start',
                'record_created': True,
            }

        elif action == 'step_update':
            # Update step status
            step_name = event.get('step_name', '')
            step_status = event.get('step_status', '')
            result = event.get('result')
            error = event.get('error')

            if not step_name:
                raise ValueError("step_name is required for step_update action")

            db.update_step_status(
                execution_id=execution_id,
                step_name=step_name,
                status=step_status,
                result=result,
                error=error,
            )

            # Get the service_request_id for return
            execution = db.get_execution(execution_id)
            service_request_id = execution.get('service_request_id') if execution else None

            return {
                'statusCode': 200,
                'tracked': True,
                'execution_id': execution_id,
                'service_request_id': service_request_id,
                'action': 'step_update',
                'step_name': step_name,
                'step_status': step_status,
            }

        elif action == 'complete':
            # Mark execution as completed
            final_result = event.get('result', {})

            db.update_execution_status(
                execution_id=execution_id,
                status='SUCCEEDED',
                final_result=final_result,
            )

            return {
                'statusCode': 200,
                'tracked': True,
                'execution_id': execution_id,
                'action': 'complete',
                'status': 'SUCCEEDED',
            }

        elif action == 'fail':
            # Mark execution as failed
            error_message = event.get('error', 'Execution failed')

            db.update_execution_status(
                execution_id=execution_id,
                status='FAILED',
                error_message=error_message,
            )

            return {
                'statusCode': 200,
                'tracked': True,
                'execution_id': execution_id,
                'action': 'fail',
                'status': 'FAILED',
            }

        else:
            raise ValueError(f"Unknown action: {action}")

    except Exception as e:
        logger.error(f"Status tracking error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'tracked': False,
            'execution_id': event.get('execution_id', ''),
            'error': str(e),
        }
