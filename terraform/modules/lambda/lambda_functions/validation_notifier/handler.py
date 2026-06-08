"""
Validation Notifier Lambda Function
Sends immediate Slack notification after ValidateIntake step passes.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Send immediate Slack notification after successful validation.

    Input event:
    {
        "execution_id": "abc123-def456",
        "service_request_id": "SR-20260608-0042",
        "slack_channel": "C123456",
        "slack_user": "U789012",
        "project_name": "CustomerAPI",
        "intake": {...}
    }

    Output:
    {
        "statusCode": 200,
        "notification_sent": true,
        "message_ts": "1234567890.123456"
    }
    """
    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError

        execution_id = event.get('execution_id', 'unknown')
        service_request_id = event.get('service_request_id', 'N/A')
        slack_channel = event.get('slack_channel')
        slack_user = event.get('slack_user')
        project_name = event.get('project_name', 'Unknown Project')

        if not slack_channel:
            logger.warning("No Slack channel provided, skipping notification")
            return {
                'statusCode': 200,
                'notification_sent': False,
                'reason': 'No Slack channel provided',
            }

        # Initialize Slack client
        slack_token = os.environ.get('SLACK_BOT_TOKEN')
        if not slack_token:
            logger.error("SLACK_BOT_TOKEN not set")
            return {
                'statusCode': 500,
                'notification_sent': False,
                'reason': 'SLACK_BOT_TOKEN not configured',
            }

        client = WebClient(token=slack_token)

        # Build message
        message = build_validation_success_message(
            service_request_id=service_request_id,
            project_name=project_name,
            user_id=slack_user,
        )

        # Send to Slack
        response = client.chat_postMessage(
            channel=slack_channel,
            blocks=message['blocks'],
            text=message['text'],
        )

        logger.info(
            f"Validation notification sent for {service_request_id} "
            f"to channel {slack_channel}"
        )

        return {
            'statusCode': 200,
            'notification_sent': True,
            'message_ts': response.get('ts'),
            'service_request_id': service_request_id,
        }

    except Exception as e:
        logger.error(f"Notification error: {str(e)}", exc_info=True)
        # Don't fail the workflow if notification fails
        return {
            'statusCode': 500,
            'notification_sent': False,
            'error': str(e),
        }


def build_validation_success_message(
    service_request_id: str,
    project_name: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Build Slack message blocks for validation success notification.

    Args:
        service_request_id: Service Request ID (e.g., SR-20260608-0042)
        project_name: Name of the project
        user_id: Slack user ID to mention

    Returns:
        Dictionary with 'text' and 'blocks' for Slack message
    """
    return {
        'text': f'✅ Onboarding request validated for {project_name}',
        'blocks': [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': '✅ Your Onboarding Request is Being Processed',
                    'emoji': True,
                },
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': (
                        f"<@{user_id}> Your infrastructure onboarding request for "
                        f"*{project_name}* has been validated and is now in progress."
                    ),
                },
            },
            {'type': 'divider'},
            {
                'type': 'section',
                'fields': [
                    {
                        'type': 'mrkdwn',
                        'text': f'*🎫 Service Request ID:*\n`{service_request_id}`',
                    },
                    {
                        'type': 'mrkdwn',
                        'text': '*⏱️ Estimated Time:*\n~30-45 seconds',
                    },
                ],
            },
            {'type': 'divider'},
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': (
                        '💡 *Track Your Request:*\n'
                        f'Use `/aws-det-onboard-status` and enter `{service_request_id}` '
                        'to check progress anytime.'
                    ),
                },
            },
            {
                'type': 'context',
                'elements': [
                    {
                        'type': 'mrkdwn',
                        'text': (
                            "You'll receive another notification when your "
                            "infrastructure is ready. 🚀"
                        ),
                    }
                ],
            },
        ],
    }
