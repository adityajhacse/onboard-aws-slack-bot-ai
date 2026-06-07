# Code for the Slack bot : Aditya Jha
import json
import logging
import os
import ssl
from pathlib import Path

import certifi
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient
# To enable loggin output

from ai_orchestrator import DetChatOrchestrator
from github_api import GitHubApiError, github_process, list_org_repositories
from hcp_terraform import HcpTerraformError, create_project_with_workspaces
from modal_lib import (
    build_processing_view,
    build_processed_confirmation_view,
    build_submission_summary_view,
    extract_intake_submission,
    welcome_page,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[key] = value


_load_dotenv(_REPO_ROOT / ".env")

logging.basicConfig(level=logging.INFO)

# Full intake is too large for Slack view private_metadata; stash until summary Submit.
_pending_full_intake_by_user: dict[str, dict] = {}
chat_orchestrator = DetChatOrchestrator()
_processed_message_keys: set[str] = set()

ssl_context = ssl.create_default_context(cafile=certifi.where())
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"], ssl=ssl_context)
app = App(client=client)


@app.command("/aws-det-poc")
def aws_det_poc(ack, body, client):
    ack()
    welcome_page(body, client, body.get("channel_id"))


@app.command("/aws-det-onboard")
def aws_det_chat(ack, body, client, respond):
    channel_id = (body.get("channel_id") or "").strip()
    if not _channel_allowed(channel_id):
        # Use the slash-command response instead of chat.postEphemeral so this
        # works when channel_id is missing or the bot cannot resolve the channel.
        ack(
            text="This channel is not enabled for DET chatbot sessions.",
            response_type="ephemeral",
        )
        return

    ack()
    team_id = body.get("team_id", "")
    user_id = body.get("user_id", "")
    text = body.get("text", "")

    try:
        starter = client.chat_postMessage(
            channel=channel_id,
            text="Starting DET chatbot session...",
        )
        thread_ts = starter.get("ts") or "default"
    except SlackApiError as exc:
        error = (exc.response or {}).get("error", "unknown")
        logging.warning("Could not create a threaded chatbot starter message: %s", error)
        response = chat_orchestrator.handle_message(
            team_id=team_id,
            channel_id=channel_id,
            user_id=user_id,
            thread_ts="default",
            text=text,
            slack_user={"id": user_id},
        )
        fallback_hint = _slash_fallback_hint(has_text=bool(text.strip()))
        kwargs: dict = {
            "text": response.text + fallback_hint,
            "response_type": "in_channel",
        }
        if response.blocks:
            kwargs["blocks"] = _with_context_hint_blocks(
                response.blocks,
                fallback_hint.strip(),
            )
        respond(**kwargs)
        return

    response = chat_orchestrator.handle_message(
        team_id=team_id,
        channel_id=channel_id,
        user_id=user_id,
        thread_ts=thread_ts,
        text=text,
        slack_user={"id": user_id},
    )
    client.chat_update(
        channel=channel_id,
        ts=thread_ts,
        text=_with_thread_hint(response.text),
        blocks=_with_thread_hint_blocks(response.blocks),
    )


@app.event("message")
def handle_chat_message(ack, body, event, client):
    ack()
    logging.info(
        "Slack message event subtype=%s channel_type=%s channel=%s user=%s thread_ts=%s ts=%s has_text=%s",
        event.get("subtype") or "",
        event.get("channel_type") or "",
        event.get("channel") or "",
        event.get("user") or "",
        event.get("thread_ts") or "",
        event.get("ts") or "",
        bool((event.get("text") or "").strip()),
    )

    if event.get("subtype"):
        if event.get("subtype") == "message_replied":
            _handle_message_replied_event(body, event, client)
        elif event.get("bot_id"):
            logging.info(
                "Ignoring bot-authored Slack message subtype=%s channel=%s ts=%s",
                event.get("subtype"),
                event.get("channel") or "",
                event.get("ts") or "",
            )
        return

    if event.get("bot_id"):
        logging.info(
            "Ignoring bot-authored Slack message channel=%s ts=%s",
            event.get("channel") or "",
            event.get("ts") or "",
        )
        return

    channel_type = event.get("channel_type")
    channel_id = event.get("channel", "")
    user_id = event.get("user", "")
    thread_ts = event.get("thread_ts") or event.get("ts") or "default"
    team_id = _team_id(body, event)
    is_chat_session_reply = False

    if channel_type != "im":
        if not event.get("thread_ts"):
            logging.info(
                "Ignoring top-level channel message; use /aws-det-onboard to start a DET thread session."
            )
            return
        if not _channel_allowed(channel_id):
            return
        session = chat_orchestrator.find_thread_session(
            channel_id=channel_id,
            thread_ts=thread_ts,
            user_id=user_id,
        )
        is_chat_session_reply = session is not None
        if not is_chat_session_reply:
            return
        team_id = session.team_id or team_id
        logging.info(
            "Continuing DET chatbot thread session channel=%s thread_ts=%s user=%s",
            channel_id,
            thread_ts,
            user_id,
        )

    if channel_type == "im":
        thread_ts = event.get("thread_ts") or event.get("ts") or "default"

    if channel_type not in {"im", "channel", "group", "mpim"} and not is_chat_session_reply:
        return

    if not _mark_message_processed(channel_id, user_id, event.get("ts", "")):
        return

    processing = _post_processing_message(client, channel_id, thread_ts)
    response = chat_orchestrator.handle_message(
        team_id=team_id,
        channel_id=channel_id,
        user_id=user_id,
        thread_ts=thread_ts,
        text=event.get("text", ""),
        slack_user={"id": user_id},
    )
    _post_or_update_thread_response(
        client=client,
        channel_id=channel_id,
        thread_ts=thread_ts,
        response=response,
        processing_ts=processing,
    )


def _handle_message_replied_event(body, event, client):
    parent = event.get("message") or {}
    channel_id = event.get("channel") or parent.get("channel", "")
    thread_ts = parent.get("thread_ts") or parent.get("ts") or event.get("thread_ts")
    if not channel_id or not thread_ts:
        return

    session = chat_orchestrator.find_thread_session(
        channel_id=channel_id,
        thread_ts=thread_ts,
    )
    if session is None:
        logging.info(
            "Ignoring message_replied event without DET session channel=%s thread_ts=%s",
            channel_id,
            thread_ts,
        )
        return

    latest_reply, read_error = _latest_user_thread_reply(client, channel_id, thread_ts)
    if latest_reply is None:
        logging.info(
            "Could not find user reply for message_replied event channel=%s thread_ts=%s",
            channel_id,
            thread_ts,
        )
        if read_error:
            _post_thread_diagnostic(
                client,
                channel_id,
                thread_ts,
                (
                    "I saw a thread update, but I could not read the reply text. "
                    f"Slack returned `{read_error}`. Please confirm the app has "
                    "`channels:history` and is reinstalled after adding the scope."
                ),
            )
        return

    user_id = latest_reply.get("user", "")
    if user_id != session.user_id:
        logging.info(
            "Ignoring thread reply from non-session user channel=%s thread_ts=%s user=%s",
            channel_id,
            thread_ts,
            user_id,
        )
        return

    if not _mark_message_processed(channel_id, user_id, latest_reply.get("ts", "")):
        return

    logging.info(
        "Continuing DET chatbot thread session from message_replied channel=%s thread_ts=%s user=%s",
        channel_id,
        thread_ts,
        user_id,
    )
    processing = _post_processing_message(client, channel_id, thread_ts)
    response = chat_orchestrator.handle_message(
        team_id=session.team_id or _team_id(body, event),
        channel_id=channel_id,
        user_id=user_id,
        thread_ts=thread_ts,
        text=latest_reply.get("text", ""),
        slack_user={"id": user_id},
    )
    _post_or_update_thread_response(
        client=client,
        channel_id=channel_id,
        thread_ts=thread_ts,
        response=response,
        processing_ts=processing,
    )


def _latest_user_thread_reply(client, channel_id, thread_ts):
    try:
        result = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            # We only need the newest reply; lower limit reduces Slack API latency.
            limit=20,
        )
    except SlackApiError as exc:
        error = (exc.response or {}).get("error", "unknown")
        logging.warning("Could not read Slack thread replies: %s", error)
        return None, error

    messages = result.get("messages") or []
    for message in reversed(messages):
        if message.get("ts") == thread_ts:
            continue
        if message.get("bot_id"):
            continue
        if message.get("subtype"):
            continue
        if not (message.get("text") or "").strip():
            continue
        return message, ""
    return None, ""


def _post_thread_diagnostic(client, channel_id, thread_ts, text):
    try:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=text,
        )
    except SlackApiError as exc:
        error = (exc.response or {}).get("error", "unknown")
        logging.warning("Could not post thread diagnostic: %s", error)


def _post_processing_message(client, channel_id, thread_ts):
    try:
        processing = client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="App is processing your request...",
        )
    except SlackApiError as exc:
        error = (exc.response or {}).get("error", "unknown")
        logging.warning("Could not post processing status message: %s", error)
        return ""
    return processing.get("ts") or ""


def _post_or_update_thread_response(client, channel_id, thread_ts, response, processing_ts):
    if processing_ts:
        try:
            client.chat_update(
                channel=channel_id,
                ts=processing_ts,
                text=response.text,
                blocks=response.blocks,
            )
            return
        except SlackApiError as exc:
            error = (exc.response or {}).get("error", "unknown")
            logging.warning("Could not update processing status message: %s", error)

    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=response.text,
        blocks=response.blocks,
    )


@app.action("det_chat_approve")
def handle_det_chat_approve(ack, body, respond):
    ack()
    session_key = _action_value(body)
    response = chat_orchestrator.approve(
        session_key=session_key,
        slack_user=body.get("user") or {},
    )
    _respond_to_action(respond, response.text, response.blocks)


@app.action("det_chat_cancel")
def handle_det_chat_cancel(ack, body, respond):
    ack()
    response = chat_orchestrator.cancel(session_key=_action_value(body))
    _respond_to_action(respond, response.text, response.blocks)


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

    github_process(full_intake, user, channel_id, client)

    environments = list(full_intake.get("environments") or [])
    project_slug = (full_intake.get("project_slug") or "").strip().lower()
    terraform_repo = (full_intake.get("terraform_repo") or "").strip()
    workspace_names = dict(full_intake.get("workspace_names") or {})

    try:
        created = create_project_with_workspaces(
            project_name=project_name,
            project_slug=project_slug,
            environments=environments,
            terraform_repo=terraform_repo,
            workspace_names=workspace_names,
        )
        created_project_name = created["project_name"]
        created_workspaces = created.get("workspace_names", [])
        success = True
        detail = (
            "Created workspaces: " + ", ".join(created_workspaces)
            if created_workspaces
            else "No environment workspaces were created."
        )
    except HcpTerraformError as exc:
        logging.exception("Failed to create HCP Terraform project")
        created_project_name = project_name
        success = False
        detail = str(exc)

    client.views_update(
        view_id=view["id"],
        view=build_processed_confirmation_view(
            success=success,
            project_name=created_project_name,
            detail=detail,
        ),
    )


def _parse_private_metadata(raw_metadata):
    if not raw_metadata:
        return {}
    try:
        return json.loads(raw_metadata)
    except json.JSONDecodeError:
        return {}


def _action_value(body):
    actions = body.get("actions") or []
    if not actions:
        return ""
    return actions[0].get("value", "")


def _respond_to_action(respond, text, blocks=None):
    kwargs = {
        "text": text,
        "response_type": "in_channel",
        "replace_original": False,
    }
    if blocks:
        kwargs["blocks"] = blocks
    respond(**kwargs)


def _mark_message_processed(channel_id, user_id, message_ts):
    if not message_ts:
        return True
    key = f"{channel_id}:{user_id}:{message_ts}"
    if key in _processed_message_keys:
        return False
    _processed_message_keys.add(key)
    if len(_processed_message_keys) > 1000:
        _processed_message_keys.clear()
    return True


def _team_id(body, event):
    team = body.get("team") or {}
    return event.get("team") or body.get("team_id") or team.get("id", "")


def _with_thread_hint(text):
    return text + "\n\nReply in this thread with the request details or corrections."


def _with_thread_hint_blocks(blocks):
    hint = {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "Reply in this thread with the request details or corrections.",
            }
        ],
    }
    if not blocks:
        return None
    return blocks + [hint]


def _with_context_hint_blocks(blocks, hint_text):
    if not hint_text:
        return blocks
    return blocks + [
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": hint_text}],
        }
    ]


def _slash_fallback_hint(has_text):
    if has_text:
        return (
            "\n\nI could not create a Slack thread in this channel, so I posted this "
            "through the slash-command response. Buttons still work here. For "
            "back-and-forth follow-up messages in this channel, invite the bot first."
        )
    return (
        "\n\nI could not create a Slack thread in this channel because the bot cannot "
        "post here yet. Either invite the bot to the channel and run `/aws-det-onboard` "
        "again, or send the full request in one command like `/aws-det-onboard Create a "
        "Dev EMS project in us-east-1, small VPC, service EMS API, team DL "
        "ems-team@example.com because this is for a new workload.`"
    )


def _channel_allowed(channel_id):
    raw = os.environ.get("DET_ALLOWED_CHANNELS", "").strip()
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            allowed = {str(value).strip() for value in parsed if str(value).strip()}
        except json.JSONDecodeError:
            allowed = set()
    else:
        allowed = {value.strip() for value in raw.split(",") if value.strip()}
    return not allowed or channel_id in allowed


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
