"""
Handlers for the /aws-det-onboard-status slash command:
  - If an SR-xxx ID is passed directly, looks it up and shows status.
  - Otherwise prompts the user to provide their Service Request ID.

Register by calling register(app) after the Slack App is created.
"""

import logging

from status_api_client import (
    StatusApiClient,
    build_error_message,
    build_not_found_message,
    build_prompt_message,
    format_status_message,
)


def register(app) -> None:
    """Attach the /aws-det-onboard-status command handler to *app*."""

    @app.command("/aws-det-onboard-status")
    def aws_det_onboard_status(ack, body, client, respond):
        ack()

        user_id = body.get("user_id", "")
        channel_id = body.get("channel_id", "")
        text = body.get("text", "").strip()

        if text and text.upper().startswith("SR-"):
            _show_status(user_id, text.upper(), respond)
        else:
            _prompt_for_service_request_id(user_id, respond)


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _prompt_for_service_request_id(user_id, respond):
    try:
        message = build_prompt_message(user_id)
        respond(
            text=message["text"],
            blocks=message["blocks"],
            response_type="ephemeral",
        )
    except Exception as exc:
        logging.error("Failed to prompt for SR ID: %s", exc, exc_info=True)
        respond(
            text=f"<@{user_id}> Please provide your Service Request ID (e.g., `SR-20260608-0042`).",
            response_type="ephemeral",
        )


def _show_status(user_id, service_request_id, respond):
    try:
        status_client = StatusApiClient()
        execution = status_client.get_status(service_request_id)

        if not execution:
            message = build_not_found_message(service_request_id, user_id)
            respond(
                text=message["text"],
                blocks=message["blocks"],
                response_type="ephemeral",
            )
            return

        message = format_status_message(execution, user_id)
        respond(
            text=message["text"],
            blocks=message["blocks"],
            response_type="ephemeral",
        )

    except Exception as exc:
        logging.error("Status lookup error: %s", exc, exc_info=True)
        message = build_error_message(user_id)
        respond(
            text=message["text"],
            blocks=message["blocks"],
            response_type="ephemeral",
        )
