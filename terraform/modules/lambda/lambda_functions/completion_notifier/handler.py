import json
import logging
import os
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Send Slack notification when workflow completes or fails.

    Input event:
    {
        "execution_id": "abc123",
        "status": "SUCCEEDED" | "FAILED",
        "slack_channel": "C0123456789",
        "slack_user": "U0123456789",
        "project_name": "EMS",
        "result": { final results },
        "error": "optional error message"
    }

    Output:
    {
        "statusCode": 200,
        "notified": true,
        "message_ts": "1234567890.123456"
    }
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        slack_token = os.environ.get('SLACK_BOT_TOKEN', '')
        if not slack_token:
            logger.warning("SLACK_BOT_TOKEN not set, skipping notification")
            return {
                'statusCode': 200,
                'notified': False,
                'reason': 'SLACK_BOT_TOKEN not configured',
            }

        execution_id = event.get('execution_id', '')
        status = event.get('status', '')
        slack_channel = event.get('slack_channel', '')
        slack_user = event.get('slack_user', '')
        project_name = event.get('project_name', 'Unknown Project')
        result = event.get('result', {})
        error = event.get('error')

        if not slack_channel:
            logger.warning("No slack_channel provided, skipping notification")
            return {
                'statusCode': 200,
                'notified': False,
                'reason': 'No slack_channel provided',
            }

        # Import Slack SDK
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
        except ImportError:
            logger.error("slack_sdk not available in Lambda environment")
            return {
                'statusCode': 500,
                'notified': False,
                'error': 'slack_sdk not available',
            }

        client = WebClient(token=slack_token)

        # Build notification message
        if status == 'SUCCEEDED':
            message = _build_success_message(
                project_name, execution_id, slack_user, result
            )
            color = 'good'
        else:
            message = _build_failure_message(
                project_name, execution_id, slack_user, error
            )
            color = 'danger'

        # Send Slack message
        try:
            response = client.chat_postMessage(
                channel=slack_channel,
                text=message['text'],
                blocks=message.get('blocks'),
                attachments=[
                    {
                        'color': color,
                        'text': message.get('attachment_text', ''),
                    }
                ] if message.get('attachment_text') else None,
            )

            logger.info(f"Sent Slack notification to {slack_channel}: {response['ts']}")

            return {
                'statusCode': 200,
                'notified': True,
                'message_ts': response['ts'],
                'channel': slack_channel,
            }

        except SlackApiError as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return {
                'statusCode': 500,
                'notified': False,
                'error': str(e),
            }

    except Exception as e:
        logger.error(f"Notification error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'notified': False,
            'error': str(e),
        }


def _build_success_message(
    project_name: str,
    execution_id: str,
    slack_user: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Build success notification message."""

    # Extract result details
    project_id = result.get('project_id', '')
    project_display = result.get('project_name', project_name)
    workspaces = result.get('configured_workspaces', [])
    file_url = result.get('file_url', '')
    branch_name = result.get('branch_name', '')

    # Count successful workspaces
    successful_workspaces = [
        w for w in workspaces
        if isinstance(w, dict) and w.get('configured', False)
    ]
    workspace_names = [w.get('workspace_name', '') for w in successful_workspaces]

    attachment_text = '\n'.join([
        f"✅ Project: *{project_display}*",
        f"✅ HCP Terraform Project ID: `{project_id}`" if project_id else "",
        f"✅ GitHub Branch: `{branch_name}`" if branch_name else "",
        f"✅ GitHub File: {file_url}" if file_url else "",
        f"✅ Workspaces Created: {', '.join(workspace_names)}" if workspace_names else "",
    ])

    return {
        'text': f"🎉 Onboarding completed for *{project_name}*",
        'blocks': [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': f'🎉 Onboarding Complete: {project_name}',
                }
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"Requested by: <@{slack_user}>\nExecution ID: `{execution_id}`"
                }
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': attachment_text,
                }
            },
        ],
        'attachment_text': attachment_text,
    }


def _build_failure_message(
    project_name: str,
    execution_id: str,
    slack_user: str,
    error: str | None,
) -> dict[str, Any]:
    """Build failure notification message."""

    error_text = error or "Workflow execution failed. Check CloudWatch logs for details."

    return {
        'text': f"❌ Onboarding failed for *{project_name}*",
        'blocks': [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': f'❌ Onboarding Failed: {project_name}',
                }
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"Requested by: <@{slack_user}>\nExecution ID: `{execution_id}`"
                }
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"*Error:*\n```{error_text}```"
                }
            },
            {
                'type': 'context',
                'elements': [
                    {
                        'type': 'mrkdwn',
                        'text': 'Check AWS Step Functions console for detailed execution history.'
                    }
                ]
            },
        ],
        'attachment_text': f"Error: {error_text}",
    }
