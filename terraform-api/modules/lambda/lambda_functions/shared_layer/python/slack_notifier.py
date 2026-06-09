"""
Shared Slack notification helper for Lambda step failure alerts.
"""
import logging
import os

logger = logging.getLogger(__name__)


def notify_step_failure(
    *,
    step_name: str,
    execution_id: str,
    slack_channel: str,
    slack_user: str = "",
    project_name: str = "",
    error: str = "",
) -> None:
    """
    Send a Slack message when a Lambda step fails.

    Silently skips if SLACK_BOT_TOKEN or slack_channel is absent so that
    missing config never causes an additional exception inside an error handler.
    """
    slack_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not slack_token or not slack_channel:
        logger.warning(
            "Skipping Slack failure notification for step %s: missing token or channel",
            step_name,
        )
        return

    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except ImportError:
        logger.warning("slack_sdk not available; skipping failure notification for step %s", step_name)
        return

    sr_id = _get_sr_id(execution_id)
    project_label = f" for *{project_name}*" if project_name else ""
    user_mention = f" <@{slack_user}>" if slack_user else ""

    text = (
        f":warning:{user_mention} Step *{step_name}* failed{project_label}.\n"
        f"Check the full status with: `/aws-det-onboard-status {sr_id}`"
    )

    try:
        client = WebClient(token=slack_token)
        client.chat_postMessage(channel=slack_channel, text=text)
        logger.info("Sent failure notification for step %s to %s", step_name, slack_channel)
    except SlackApiError as exc:
        logger.warning("Failed to send step failure notification: %s", exc)
    except Exception as exc:
        logger.warning("Unexpected error sending step failure notification: %s", exc)


def _get_sr_id(execution_id: str) -> str:
    """Look up the Service Request ID from DynamoDB. Returns 'N/A' on any error."""
    if not execution_id:
        return "N/A"
    try:
        from dynamodb_helper import get_helper
        db = get_helper()
        execution = db.get_execution(execution_id)
        if execution:
            return execution.get("service_request_id", "N/A")
    except Exception as exc:
        logger.warning("Could not fetch SR ID for notification: %s", exc)
    return "N/A"
