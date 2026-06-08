"""
Status API Client
Client for calling the status lookup Lambda via API Gateway.
"""

import logging
import os
from typing import Any, Optional

import certifi
import requests

logger = logging.getLogger(__name__)


class StatusApiClient:
    """Client for status lookup API."""

    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize the status API client.

        Args:
            api_url: API Gateway URL for status lookup.
                     Defaults to STATUS_API_URL environment variable.
        """
        self.api_url = api_url or os.environ.get('STATUS_API_URL', '')
        if not self.api_url:
            logger.warning("STATUS_API_URL not set")

    def get_status(self, service_request_id: str) -> Optional[dict[str, Any]]:
        """
        Get execution status by Service Request ID.

        Args:
            service_request_id: Service Request ID (e.g., SR-20260608-1234)

        Returns:
            Execution data or None if not found/error
        """
        if not self.api_url:
            logger.error("STATUS_API_URL not configured")
            return None

        try:
            # If api_url already ends with /status, don't add it again
            if self.api_url.endswith('/status'):
                url = self.api_url
            else:
                url = f"{self.api_url}/status"

            params = {'service_request_id': service_request_id}

            logger.info(f"Fetching status for {service_request_id} from {url}")

            response = requests.get(url, params=params, timeout=10, verify=certifi.where())

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"Service Request ID {service_request_id} not found")
                return None
            else:
                logger.error(
                    f"API returned status {response.status_code}: {response.text}"
                )
                return None

        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return None


def format_status_message(execution: dict[str, Any], user_id: str) -> dict[str, Any]:
    """
    Format execution status as Slack message blocks.

    Args:
        execution: Execution data from API
        user_id: Slack user ID to mention

    Returns:
        Dictionary with 'text' and 'blocks' for Slack message
    """
    service_request_id = execution.get('service_request_id', 'N/A')
    project_name = execution.get('project_name', 'Unknown')
    status = execution.get('status', 'UNKNOWN')
    time_display = execution.get('time_display', 'Unknown')

    # Status emoji
    status_emoji = get_status_emoji(status)

    # Step statuses
    steps = execution.get('steps', {})
    step_validate = steps.get('validate_intake', 'UNKNOWN')
    step_branch = steps.get('github_branch', 'UNKNOWN')
    step_commit = steps.get('github_commit', 'UNKNOWN')
    step_project = steps.get('hcp_project', 'UNKNOWN')
    step_workspaces = steps.get('workspaces', 'UNKNOWN')
    step_variables = steps.get('variables', 'UNKNOWN')

    # Build message blocks
    blocks = [
        {
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': f'{status_emoji} Service Request Status',
                'emoji': True,
            },
        },
        {
            'type': 'section',
            'fields': [
                {'type': 'mrkdwn', 'text': f'*🎫 Request ID:*\n`{service_request_id}`'},
                {'type': 'mrkdwn', 'text': f'*📦 Project:*\n{project_name}'},
                {'type': 'mrkdwn', 'text': f'*🔄 Status:*\n{status}'},
                {'type': 'mrkdwn', 'text': f'*⏱️ Time:*\n{time_display}'},
            ],
        },
        {'type': 'divider'},
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': '*Pipeline Steps:*',
            },
        },
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': format_pipeline_steps(
                    step_validate,
                    step_branch,
                    step_commit,
                    step_project,
                    step_workspaces,
                    step_variables,
                ),
            },
        },
        {'type': 'divider'},
    ]

    # Add status-specific footer
    blocks.append(build_status_footer(status, user_id, execution))

    return {
        'text': f'{status_emoji} Status for {service_request_id}: {status}',
        'blocks': blocks,
    }


def get_status_emoji(status: str) -> str:
    """Get emoji for overall status."""
    return {
        'RUNNING': '🔄',
        'SUCCEEDED': '✅',
        'FAILED': '❌',
    }.get(status, '❓')


def get_step_emoji(status: str) -> str:
    """Get emoji for step status."""
    return {
        'SUCCEEDED': '✅',
        'RUNNING': '🔄',
        'FAILED': '❌',
        'PENDING': '⏳',
        'SKIPPED': '⏭️',
    }.get(status, '❓')


def format_pipeline_steps(
    step_validate: str,
    step_branch: str,
    step_commit: str,
    step_project: str,
    step_workspaces: str,
    step_variables: str,
) -> str:
    """Format pipeline steps as text."""
    return (
        f"{get_step_emoji(step_validate)} *Validate Intake* - {step_validate}\n"
        f"{get_step_emoji(step_branch)} *Create GitHub Branch* - {step_branch}\n"
        f"{get_step_emoji(step_commit)} *Commit to GitHub* - {step_commit}\n"
        f"{get_step_emoji(step_project)} *Create HCP Project* - {step_project}\n"
        f"{get_step_emoji(step_workspaces)} *Create Workspaces* - {step_workspaces}\n"
        f"{get_step_emoji(step_variables)} *Configure workspaces Variables* - {step_variables}"
        f"{get_step_emoji(step_variables)} *Configure vault stores* - Pending"
    )


def build_status_footer(status: str, user_id: str, execution: dict[str, Any]) -> dict:
    """Build status-specific footer block."""
    if status == 'RUNNING':
        return {
            'type': 'context',
            'elements': [
                {
                    'type': 'mrkdwn',
                    'text': (
                        f"💡 <@{user_id}> Your request is being processed. "
                        "Check back in a moment or wait for completion notification."
                    ),
                }
            ],
        }
    elif status == 'SUCCEEDED':
        return {
            'type': 'context',
            'elements': [
                {
                    'type': 'mrkdwn',
                    'text': (
                        f"✅ <@{user_id}> Your infrastructure is ready! "
                        "Check your notifications for resource links."
                    ),
                }
            ],
        }
    elif status == 'FAILED':
        error_msg = execution.get('error_message', 'Unknown error')
        return {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': (
                    f"*❌ Error:*\n```{error_msg}```\n\n"
                    f"<@{user_id}> Please contact support for assistance."
                ),
            },
        }
    else:
        return {
            'type': 'context',
            'elements': [
                {
                    'type': 'mrkdwn',
                    'text': f"<@{user_id}> Status: {status}",
                }
            ],
        }


def build_not_found_message(service_request_id: str, user_id: str) -> dict[str, Any]:
    """Build message for when Service Request ID is not found."""
    return {
        'text': f'❌ Service Request ID `{service_request_id}` not found',
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': (
                        f"❌ <@{user_id}> I couldn't find a request with ID "
                        f"`{service_request_id}`.\n\n"
                        "*Please check:*\n"
                        "• ID is correct (case-sensitive)\n"
                        "• Request was submitted less than 90 days ago\n"
                        "• You're checking in the correct workspace"
                    ),
                },
            }
        ],
    }


def build_prompt_message(user_id: str) -> dict[str, Any]:
    """Build message prompting user for Service Request ID."""
    return {
        'text': 'Please provide your Service Request ID',
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': (
                        f"<@{user_id}> To check your onboarding status, please reply with "
                        "your *Service Request ID*.\n\n"
                        "*Example:* `SR-20260608-0042`\n\n"
                        "_You received this ID when you submitted your onboarding request._"
                    ),
                },
            }
        ],
    }


def build_error_message(user_id: str) -> dict[str, Any]:
    """Build generic error message."""
    return {
        'text': '❌ Error retrieving status',
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': (
                        f"❌ <@{user_id}> An error occurred while retrieving your status. "
                        "Please try again later or contact support if the issue persists."
                    ),
                },
            }
        ],
    }
