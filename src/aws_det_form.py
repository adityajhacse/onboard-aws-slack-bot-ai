"""
Handlers for the /aws-det-onboard-form slash command and all form-related activity:
  - /aws-det-onboard-form command  →  opens the DET intake modal (welcome_page)
  - det_chat_open_form action  →  re-opens the form from a chat button
  - det_intake_modal view  →  first-step submission (pushes summary view)
  - terraform_repo options  →  dynamic GitHub repo list for the form
  - det_summary_modal view  →  final submission that triggers the onboarding workflow

Register everything by calling register(app, api_client) after the Slack App is created.
"""

import json
import logging
import os

from slack_sdk.errors import SlackApiError

from api_gateway_client import ApiGatewayClient, ApiGatewayError
from github_api import GitHubApiError, list_org_repositories
from modal_lib import (
    build_processed_confirmation_view,
    build_processing_view,
    build_submission_summary_view,
    extract_intake_submission,
    welcome_page,
)

# Full intake is too large for Slack view private_metadata; stashed here until
# the summary modal is submitted.
_pending_full_intake_by_user: dict[str, dict] = {}


def register(app, api_client: ApiGatewayClient) -> None:
    """Attach all /aws-det-onboard-form form handlers to *app*."""

    @app.command("/aws-det-onboard-form")
    def aws_det_onboard_form(ack, body, client):
        ack()
        welcome_page(body, client, body.get("channel_id"))

    @app.action("det_chat_open_form")
    def handle_det_chat_open_form(ack, body, client):
        ack()
        channel_id = (body.get("channel") or {}).get("id", "")
        user_id = (body.get("user") or {}).get("id", "")
        welcome_page(
            {
                "trigger_id": body.get("trigger_id", ""),
                "user_id": user_id,
            },
            client,
            channel_id,
        )

    @app.view("det_intake_modal")
    def handle_det_intake_submit(ack, body, view, client):
        intake = extract_intake_submission(view)
        uid = (body.get("user") or {}).get("id")
        if uid:
            _pending_full_intake_by_user[uid] = intake
        ack(
            response_action="push",
            view=build_submission_summary_view(view),
        )

    @app.options("terraform_repo")
    def handle_terraform_repo_options(ack, body, logger):
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        owner = os.environ.get("GITHUB_OWNER", "adityajhacse").strip()
        query = (body.get("value") or "").strip()
        if not token or not owner:
            ack(options=[])
            return

        try:
            repos = list_org_repositories(owner, token, query=query, limit=100)
        except GitHubApiError as exc:
            logger.warning("Could not load terraform repo options: %s", exc)
            ack(options=[])
            return

        ack(
            options=[
                {
                    "text": {"type": "plain_text", "text": repo},
                    "value": repo,
                }
                for repo in repos
            ]
        )

    @app.view("det_summary_modal")
    def handle_det_summary_submit(ack, body, view, client):
        metadata = _parse_private_metadata(view.get("private_metadata", ""))
        intake_meta = metadata.get("intake", {})
        project_name = (
            intake_meta.get("project_upper")
            or intake_meta.get("project_name")
            or "unknown-project"
        )

        user = body.get("user") or {}
        uid = user.get("id")
        full_intake = _pending_full_intake_by_user.pop(uid, None) if uid else None
        full_intake = full_intake or {}
        channel_id = metadata.get("channel_id") or ""

        ack(
            response_action="update",
            view=build_processing_view(project_name),
        )

        try:
            logging.info("Triggering onboarding workflow for %s", project_name)
            result = api_client.trigger_onboarding(
                intake=full_intake,
                slack_channel=channel_id,
                slack_user=uid,
            )

            execution_arn = result.get("executionArn", "")
            execution_id = execution_arn.split(":")[-1] if execution_arn else "unknown"

            client.views_update(
                view_id=view["id"],
                view=build_processed_confirmation_view(
                    success=True,
                    project_name=project_name,
                    detail=(
                        f"Onboarding workflow started successfully!\n\n"
                        f"Execution ID: `{execution_id}`\n\n"
                        f"The workflow is running in the background and will:\n"
                        f"1. Create GitHub branch and commit intake document\n"
                        f"2. Create HCP Terraform project\n"
                        f"3. Create workspaces for each environment\n"
                        f"4. Configure workspace variables\n\n"
                        f"You'll receive a notification when it completes.\n"
                        f"Check status with: `/aws-det-status {execution_id}`"
                    ),
                ),
            )

            if channel_id:
                try:
                    client.chat_postMessage(
                        channel=channel_id,
                        text=(
                            f"Onboarding workflow started for *{project_name}*\n"
                            f"Execution ID: `{execution_id}`\n"
                            f"Started by: <@{uid}>\n\n"
                            f"The workflow is processing in the background. "
                            f"You'll be notified when it completes."
                        ),
                    )
                except SlackApiError as exc:
                    logging.warning("Could not post workflow start message: %s", exc)

        except ApiGatewayError as exc:
            logging.exception("Failed to trigger onboarding workflow via API Gateway")
            client.views_update(
                view_id=view["id"],
                view=build_processed_confirmation_view(
                    success=False,
                    project_name=project_name,
                    detail=f"Failed to start onboarding workflow: {exc}",
                ),
            )


def _parse_private_metadata(raw_metadata: str) -> dict:
    if not raw_metadata:
        return {}
    try:
        return json.loads(raw_metadata)
    except json.JSONDecodeError:
        return {}
