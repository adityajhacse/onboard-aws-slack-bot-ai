"""
Handlers for the /aws-det-onboard-chat slash command and all DET chat-session activity:
  - /aws-det-onboard-chat command  →  starts a DET chatbot thread session
  - message event handler    →  routes thread replies and DM messages to the orchestrator
  - det_chat_approve / det_chat_cancel button actions
  - SR-XXXXXXXX DM messages  →  routed to status_api_client for lookup

Register everything by calling register(app, api_client) after the Slack App is created.
"""

import json
import logging
import os

from slack_sdk.errors import SlackApiError

from ai_orchestrator import DetChatOrchestrator
from api_gateway_client import ApiGatewayClient

# Deduplication set: prevents double-processing the same Slack message event.
_processed_message_keys: set[str] = set()


def register(app, api_client: ApiGatewayClient) -> None:
    """Attach all /aws-det-onboard-chat chat handlers to *app*."""

    chat_orchestrator = DetChatOrchestrator(api_gateway_client=api_client)

    # ------------------------------------------------------------------
    # Slash command
    # ------------------------------------------------------------------

    @app.command("/aws-det-onboard-chat")
    def aws_det_onboard_chat(ack, body, client, respond):
        channel_id = (body.get("channel_id") or "").strip()
        if not _channel_allowed(channel_id):
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

    # ------------------------------------------------------------------
    # Message event (thread replies + DM messages)
    # ------------------------------------------------------------------

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
                _handle_message_replied_event(body, event, client, chat_orchestrator)
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
        text = event.get("text", "").strip()
        thread_ts = event.get("thread_ts") or event.get("ts") or "default"
        team_id = _team_id(body, event)
        is_chat_session_reply = False

        if text.upper().startswith("SR-") and len(text) >= 9 and channel_type == "im":
            service_request_id = text.upper()
            logging.info("User %s checking status for %s", user_id, service_request_id)
            _handle_status_lookup_in_dm(client, channel_id, user_id, service_request_id)
            return

        if channel_type != "im":
            if not event.get("thread_ts"):
                logging.info(
                    "Ignoring top-level channel message; use /aws-det-onboard-chat to start a DET thread session."
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

    # ------------------------------------------------------------------
    # Button actions (approve / cancel)
    # ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _handle_message_replied_event(body, event, client, chat_orchestrator):
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


def _handle_status_lookup_in_dm(client, channel_id, user_id, service_request_id):
    from status_api_client import (
        StatusApiClient,
        format_status_message,
        build_not_found_message,
        build_error_message,
    )

    try:
        status_client = StatusApiClient()
        execution = status_client.get_status(service_request_id)

        if not execution:
            message = build_not_found_message(service_request_id, user_id)
            client.chat_postMessage(
                channel=channel_id,
                text=message["text"],
                blocks=message["blocks"],
            )
            return

        message = format_status_message(execution, user_id)
        client.chat_postMessage(
            channel=channel_id,
            text=message["text"],
            blocks=message["blocks"],
        )

    except SlackApiError as exc:
        logging.error("Slack API error in status lookup: %s", exc)
        client.chat_postMessage(
            channel=channel_id,
            text=f"❌ <@{user_id}> Error retrieving status. Please try again.",
        )
    except Exception as exc:
        logging.error("Status lookup error: %s", exc, exc_info=True)
        from status_api_client import build_error_message
        message = build_error_message(user_id)
        try:
            client.chat_postMessage(
                channel=channel_id,
                text=message["text"],
                blocks=message["blocks"],
            )
        except Exception:
            client.chat_postMessage(
                channel=channel_id,
                text=f"❌ <@{user_id}> An error occurred. Please try again.",
            )


def _action_value(body) -> str:
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


def _mark_message_processed(channel_id, user_id, message_ts) -> bool:
    if not message_ts:
        return True
    key = f"{channel_id}:{user_id}:{message_ts}"
    if key in _processed_message_keys:
        return False
    _processed_message_keys.add(key)
    if len(_processed_message_keys) > 1000:
        _processed_message_keys.clear()
    return True


def _team_id(body, event) -> str:
    team = body.get("team") or {}
    return event.get("team") or body.get("team_id") or team.get("id", "")


def _with_thread_hint(text: str) -> str:
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


def _with_context_hint_blocks(blocks, hint_text: str):
    if not hint_text:
        return blocks
    return blocks + [
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": hint_text}],
        }
    ]


def _slash_fallback_hint(has_text: bool) -> str:
    if has_text:
        return (
            "\n\nI could not create a Slack thread in this channel, so I posted this "
            "through the slash-command response. Buttons still work here. For "
            "back-and-forth follow-up messages in this channel, invite the bot first."
        )
    return (
        "\n\nI could not create a Slack thread in this channel because the bot cannot "
        "post here yet. Either invite the bot to the channel and run `/aws-det-onboard-chat` "
        "again, or send the full request in one command like `/aws-det-onboard-chat Create a "
        "Dev EMS project in us-east-1, small VPC, service EMS API, team DL "
        "ems-team@example.com because this is for a new workload.`"
    )


def _channel_allowed(channel_id: str) -> bool:
    raw = os.environ.get("DET_ALLOWED_CHANNELS", "").strip()
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            allowed = {str(v).strip() for v in parsed if str(v).strip()}
        except json.JSONDecodeError:
            allowed = set()
    else:
        allowed = {v.strip() for v in raw.split(",") if v.strip()}
    return not allowed or channel_id in allowed
