from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from det_intake import (
    ALLOWED_ENVIRONMENTS,
    ALLOWED_REGIONS,
    ALLOWED_VPC_MODELS,
    format_missing_fields,
    merge_intake_updates,
    normalize_intake,
)
from mcp_client import LocalMcpClient
from session_store import InMemorySessionStore

# Imported lazily to avoid circular imports at module load time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from api_gateway_client import ApiGatewayClient

_MAX_LLM_ATTEMPTS = 2


class LLMGatewayConnectionError(Exception):
    """Raised when the LLM gateway cannot be reached after max retries."""


@dataclass
class ChatResponse:
    text: str
    blocks: list[dict[str, Any]] | None = None


class DetChatOrchestrator:
    def __init__(
        self,
        *,
        store: InMemorySessionStore | None = None,
        mcp_client: LocalMcpClient | None = None,
        api_gateway_client: "ApiGatewayClient | None" = None,
    ) -> None:
        self.store = store or InMemorySessionStore()
        self.mcp = mcp_client or LocalMcpClient()
        self.api_client = api_gateway_client

    def handle_message(
        self,
        *,
        team_id: str,
        channel_id: str,
        user_id: str,
        thread_ts: str,
        text: str,
        slack_user: dict[str, Any] | None = None,
    ) -> ChatResponse:
        session = self.store.get_or_create(
            team_id=team_id,
            channel_id=channel_id,
            user_id=user_id,
            thread_ts=thread_ts,
        )
        clean_text = _strip_bot_mentions(text).strip()

        if _is_reset(clean_text):
            self.store.reset(session.key)
            return ChatResponse("Chat intake session reset. Send the request details to start again.")

        if not clean_text or clean_text.lower() in {"help", "start"}:
            return ChatResponse(_intro_text())

        if clean_text.lower() in {"approve", "submit", "yes"}:
            return ChatResponse(
                "Please use the Slack `Approve` button on the preview. Text approval is not accepted."
            )

        session.messages.append({"role": "user", "content": clean_text})
        try:
            updates = self._extract_updates(clean_text, session.candidate_intake)
        except LLMGatewayConnectionError as exc:
            error_desc = _format_llm_error(exc)
            return ChatResponse(
                text=f"Issue with LLM Gateway - the AI assistant is currently unavailable. {error_desc}",
                blocks=_llm_gateway_error_blocks(session.key, error_desc),
            )
        if updates:
            session.candidate_intake = merge_intake_updates(
                session.candidate_intake,
                updates,
            )
        else:
            session.candidate_intake = normalize_intake(session.candidate_intake)

        try:
            validation = self.mcp.call_tool(
                "det_validate_intake",
                {"candidate": session.candidate_intake},
            )
        except Exception as exc:
            logging.exception("MCP validation failed")
            return ChatResponse(f"MCP validation failed: {exc}")

        session.candidate_intake = validation.get("intake", session.candidate_intake)
        session.approval_state = "draft"

        if validation.get("errors"):
            self.store.save(session)
            return ChatResponse(
                "I found a few values to fix:\n"
                + "\n".join(f"- {error}" for error in validation["errors"])
                + "\n\n"
                + _draft_text(session.candidate_intake)
            )

        missing = validation.get("missing_fields") or []
        if missing:
            self.store.save(session)
            try:
                return ChatResponse(_missing_fields_text(missing, session.candidate_intake))
            except LLMGatewayConnectionError as exc:
                error_desc = _format_llm_error(exc)
                return ChatResponse(
                    text=f"Issue with LLM Gateway - the AI assistant is currently unavailable. {error_desc}",
                    blocks=_llm_gateway_error_blocks(session.key, error_desc),
                )

        try:
            preview = self.mcp.call_tool(
                "det_preview_request",
                {
                    "candidate": session.candidate_intake,
                    "slack_user": slack_user or {"id": user_id},
                },
            )
        except Exception as exc:
            logging.exception("MCP preview failed")
            return ChatResponse(f"MCP preview failed: {exc}")

        session.preview = preview
        session.approval_state = "pending_approval"
        self.store.save(session)

        preview_text = preview.get("slack_preview") or "Preview is ready."
        dry_run_note = (
            "*Dry run is enabled.* Approval will validate the flow but will not modify GitHub or HCP Terraform."
            if _dry_run_enabled()
            else "*Approval will commit to GitHub and create the HCP Terraform project.*"
        )
        full_text = preview_text + "\n\n" + dry_run_note
        return ChatResponse(
            text=_plain_text_preview(preview),
            blocks=_approval_blocks(session.key, full_text),
        )

    def approve(
        self,
        *,
        session_key: str,
        slack_user: dict[str, Any] | None = None,
    ) -> ChatResponse:
        session = self.store.get(session_key)
        if session is None:
            return ChatResponse("This chatbot session expired. Please start `/aws-det-onboard` again.")

        if session.approval_state != "pending_approval":
            return ChatResponse("There is no pending preview to approve for this session.")

        # Always validate locally first (fast, no external side-effects)
        try:
            validation = self.mcp.call_tool(
                "det_validate_intake",
                {"candidate": session.candidate_intake},
            )
        except Exception as exc:
            logging.exception("Intake validation failed")
            return ChatResponse(f"Validation failed: {exc}")

        if not validation.get("valid"):
            session.approval_state = "draft"
            self.store.save(session)
            return ChatResponse(
                "This request is no longer valid. Missing: "
                + format_missing_fields(validation.get("missing_fields") or [])
            )

        user_id = (slack_user or {}).get("id") or session.user_id
        channel_id = session.channel_id

        # Route through API Gateway → Step Functions when client is available
        if self.api_client is not None:
            try:
                result = self.api_client.trigger_onboarding(
                    intake=session.candidate_intake,
                    slack_channel=channel_id,
                    slack_user=user_id,
                )
            except Exception as exc:
                logging.exception("Failed to trigger onboarding via API Gateway")
                session.approval_state = "draft"
                self.store.save(session)
                return ChatResponse(f"Failed to start onboarding workflow: {exc}")

            execution_arn = result.get("executionArn", "")
            execution_id = execution_arn.split(":")[-1] if execution_arn else "unknown"
            project_name = session.candidate_intake.get("project_name", "your project")

            self.store.reset(session.key)
            return ChatResponse(
                f"Onboarding workflow started for *{project_name}*!\n\n"
                f"Execution ID: `{execution_id}`\n\n"
                f"The Process is running in AWS background. It will:\n"
                f"1. Create GitHub branch and commit intake document\n"
                f"2. Create HCP Terraform project\n"
                f"3. Create workspaces for each environment\n"
                f"4. Configure workspace variables\n\n"
                f"You'll receive a notification in this channel when it completes.\n"
                f"Check status with: `/aws-det-onboard-status SR-id`\n\n"
                f"Session closed. Start a new `/aws-det-onboard` request when needed."
            )

        session.approval_state = "draft"
        self.store.save(session)
        return ChatResponse(
            "Onboarding workflow cannot be started: API Gateway is not configured. "
            "Please contact your administrator."
        )

    def cancel(self, *, session_key: str) -> ChatResponse:
        self.store.reset(session_key)
        return ChatResponse("Chatbot intake cancelled. No GitHub or HCP Terraform changes were made.")

    def has_session(
        self,
        *,
        team_id: str,
        channel_id: str,
        user_id: str,
        thread_ts: str,
    ) -> bool:
        return self.store.exists(
            team_id=team_id,
            channel_id=channel_id,
            user_id=user_id,
            thread_ts=thread_ts,
        )

    def find_thread_session(
        self,
        *,
        channel_id: str,
        thread_ts: str,
        user_id: str | None = None,
        team_id: str | None = None,
    ):
        return self.store.find_thread_session(
            channel_id=channel_id,
            thread_ts=thread_ts,
            user_id=user_id,
            team_id=team_id,
        )

    def _extract_updates(
        self,
        text: str,
        current_intake: dict[str, Any],
    ) -> dict[str, Any]:
        updates = _deterministic_extract(text, current_intake)
        ai_updates = _openai_extract(text, current_intake)
        if ai_updates:
            updates = merge_intake_updates(updates, ai_updates)
        return updates


def _is_llm_connection_error(exc: Exception) -> bool:
    """Return True if *exc* indicates a network/connectivity or auth failure with the LLM gateway.

    Authentication errors (401) from LiteLLM / OpenAI-compatible gateways are treated as
    gateway-level issues (misconfigured key or gateway unreachable) rather than user errors,
    so they surface the "Issue with LLM Gateway" block with Open Form / Cancel buttons.
    """
    try:
        from openai import APIConnectionError, APITimeoutError, AuthenticationError, PermissionDeniedError
        if isinstance(exc, (APIConnectionError, APITimeoutError, AuthenticationError, PermissionDeniedError)):
            return True
    except ImportError:
        pass
    type_name = type(exc).__name__.lower()
    return any(kw in type_name for kw in ("connect", "timeout", "network", "auth", "authentication", "permission"))


def _format_llm_error(exc: Exception) -> str:
    """Return a short, user-facing description of an LLM gateway error."""
    return f"{type(exc).__name__}: {str(exc)[:120]}"


def _openai_extract(text: str, current_intake: dict[str, Any]) -> dict[str, Any]:
    provider = os.environ.get("AI_PROVIDER", "openai").strip().lower()
    if provider in {"", "none", "disabled"}:
        return {}
    if provider != "openai":
        logging.warning("Unsupported AI_PROVIDER=%s; skipping AI extraction.", provider)
        return {}

    api_key = (
        os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("AI_API_KEY", "").strip()
    )
    if not api_key:
        return {}

    try:
        import httpx
        from openai import OpenAI
    except ImportError:
        logging.warning("OpenAI SDK is not installed; skipping AI extraction.")
        return {}

    model = os.environ.get("AI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    system_prompt = (
        "You extract AWS DET onboarding intake fields from Slack messages. "
        "Return only JSON. Extract only values explicitly present in the latest "
        "message. Do not invent missing values. Allowed environments are "
        f"{', '.join(ALLOWED_ENVIRONMENTS)}. Allowed regions are "
        f"{', '.join(ALLOWED_REGIONS)}. Allowed VPC models are "
        f"{', '.join(ALLOWED_VPC_MODELS)}. "
        "Return this shape: {\"intake_updates\": {}}. Valid keys are "
        "project_name, terraform_repo, team_channel, workspace_mode, workspace_names, environments, regions, vpc_model, service_name, "
        "business_justification, members, team_dl."
    )
    user_prompt = {
        "current_intake": current_intake,
        "latest_message": text,
    }

    ssl_verify = os.environ.get("AI_SSL_VERIFY", "true").strip().lower()
    disable_ssl_verify = ssl_verify in {"0", "false", "no", "off"}
    if disable_ssl_verify:
        logging.warning(
            "AI_SSL_VERIFY disabled; TLS certificate verification is bypassed for OpenAI calls."
        )
        client = OpenAI(api_key=api_key, http_client=httpx.Client(verify=False))
    else:
        client = OpenAI(api_key=api_key)

    last_exc: Exception | None = None
    for attempt in range(_MAX_LLM_ATTEMPTS):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_prompt)},
                ],
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            updates = parsed.get("intake_updates", parsed)
            return updates if isinstance(updates, dict) else {}
        except Exception as exc:
            if _is_llm_connection_error(exc):
                last_exc = exc
                logging.warning(
                    "LLM gateway connection attempt %d/%d failed: %s",
                    attempt + 1,
                    _MAX_LLM_ATTEMPTS,
                    exc,
                )
                continue
            logging.exception("OpenAI extraction failed (non-connection error).")
            return {}

    raise LLMGatewayConnectionError(_format_llm_error(last_exc)) from last_exc


def _missing_fields_text(missing_fields: list[str], intake: dict[str, Any]) -> str:
    normalized = normalize_intake(intake)
    fields_to_ask = _fields_to_ask_now(missing_fields)
    ai_text = _openai_missing_fields_text(fields_to_ask, normalized)
    if ai_text:
        return ai_text
    return _friendly_missing_fields_text(fields_to_ask, normalized)


def _openai_missing_fields_text(
    fields_to_ask: list[str],
    intake: dict[str, Any],
) -> str:
    provider = os.environ.get("AI_PROVIDER", "openai").strip().lower()
    if provider in {"", "none", "disabled"}:
        return ""
    if provider != "openai":
        return ""

    api_key = (
        os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("AI_API_KEY", "").strip()
    )
    if not api_key:
        return ""

    try:
        import httpx
        from openai import OpenAI
    except ImportError:
        return ""

    model = os.environ.get("AI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    system_prompt = (
        "You write concise Slack follow-up messages for an AWS DET intake bot. "
        "Return only JSON with a text string. Sound warm and natural, but keep "
        "ASCII punctuation and do not use emoji. Use only facts in current_intake; "
        "do not invent missing values. Mention captured details in one short first "
        "sentence when useful. Ask only for fields_to_ask. Do not show a draft, "
        "table, JSON, or bullet checklist. Keep the response under 900 characters. "
        "Allowed environments are Dev, QA, and Prod. Allowed regions are "
        "us-east-1, us-west-2, and eu-west-1. Allowed VPC sizes are Small, "
        "Medium, and Big."
    )
    user_prompt = {
        "current_intake": intake,
        "fields_to_ask": fields_to_ask,
        "question_bank": {
            field: _question_for_missing_field(field, intake)
            for field in fields_to_ask
        },
        "response_shape": {"text": "Slack-ready follow-up text"},
    }

    ssl_verify = os.environ.get("AI_SSL_VERIFY", "true").strip().lower()
    disable_ssl_verify = ssl_verify in {"0", "false", "no", "off"}
    if disable_ssl_verify:
        logging.warning(
            "AI_SSL_VERIFY disabled; TLS certificate verification is bypassed for OpenAI calls."
        )
        client = OpenAI(api_key=api_key, http_client=httpx.Client(verify=False))
    else:
        client = OpenAI(api_key=api_key)

    last_exc: Exception | None = None
    for attempt in range(_MAX_LLM_ATTEMPTS):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.4,
                response_format={"type": "json_object"},
                max_tokens=240,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_prompt)},
                ],
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            text = str(parsed.get("text", "")).strip()
            if not text or len(text) > 1200:
                return ""
            return text
        except Exception as exc:
            if _is_llm_connection_error(exc):
                last_exc = exc
                logging.warning(
                    "LLM gateway connection attempt %d/%d failed: %s",
                    attempt + 1,
                    _MAX_LLM_ATTEMPTS,
                    exc,
                )
                continue
            logging.exception("OpenAI follow-up generation failed (non-connection error).")
            return ""

    raise LLMGatewayConnectionError(_format_llm_error(last_exc)) from last_exc


def _friendly_missing_fields_text(
    fields_to_ask: list[str],
    intake: dict[str, Any],
) -> str:
    intro = _captured_intake_sentence(intake)
    if fields_to_ask:
        questions = "\n".join(_question_for_missing_field(field, intake) for field in fields_to_ask)
        if _has_captured_intake(intake):
            return f"{intro}\n\nI just need a few more details:\n\n{questions}"
        return f"{intro}\n\n{questions}"
    return intro


def _fields_to_ask_now(missing_fields: list[str]) -> list[str]:
    ordered = [
        field
        for field in (
            "project_name",
            "terraform_repo",
            "team_channel",
            "workspace_mode",
            "workspace_names",
            "environments",
            "regions",
            "vpc_model",
            "service_name",
            "business_justification",
            "team_dl",
        )
        if field in missing_fields
    ]
    return ordered if len(ordered) <= 4 else ordered[:3]


def _question_for_missing_field(field: str, intake: dict[str, Any] | None = None) -> str:
    intake = intake or {}
    questions = {
        "project_name": "What project/workload name should I use?",
        "terraform_repo": "Which Terraform GitHub repo should the workspace use (owner/repo)?",
        "team_channel": "Which team channel should we use for this request?",
        "workspace_mode": (
            "Do you want default workspace names "
            "(`<project-name>-<env>`) or custom names per environment?"
        ),
        "workspace_names": _workspace_names_question(intake),
        "environments": "Which environment do you need (Dev, QA, Prod)?",
        "regions": "Which region should I use (us-east-1, us-west-2, eu-west-1)?",
        "vpc_model": "What VPC size do you want (Small, Medium, Big)?",
        "service_name": "What service name should I attach to this request?",
        "business_justification": "What's the business justification?",
        "team_dl": "What's your team DL email?",
    }
    return questions.get(field, f"Can you share {field}?")


def _workspace_names_question(intake: dict[str, Any]) -> str:
    environments = list(intake.get("environments") or [])
    current_names = dict(intake.get("workspace_names") or {})
    missing_envs = [env for env in environments if not current_names.get(env)]
    if len(missing_envs) == 1:
        env = missing_envs[0]
        return (
            f"Please provide a custom workspace name for `{env}` "
            f"(default would be `{(intake.get('project_slug') or 'project')}-{env.lower()}`)."
        )
    if missing_envs:
        env_list = ", ".join(missing_envs)
        return f"Please provide custom workspace names for: {env_list}."
    return "Please provide custom workspace names for each selected environment."


def _captured_intake_sentence(intake: dict[str, Any]) -> str:
    project = intake.get("project_name", "")
    environments = intake.get("environments", [])
    regions = intake.get("regions", [])
    vpc_model = intake.get("vpc_model", "")
    service = intake.get("service_name", "")

    env_text = _join_natural(environments)
    region_text = _join_natural(regions)

    if project and env_text and region_text:
        sentence = f"Got it - you're creating a {env_text} {project} project in {region_text}"
        if vpc_model:
            sentence += f" with a {vpc_model} VPC"
        if service:
            sentence += f" for {service}"
        return sentence + "."

    captured = []
    if project:
        captured.append(f"project {project}")
    if env_text:
        captured.append(f"environment {env_text}")
    if region_text:
        captured.append(f"region {region_text}")
    if vpc_model:
        captured.append(f"{vpc_model} VPC")
    if service:
        captured.append(f"service {service}")

    if captured:
        return "Got it - I have " + _join_natural(captured) + "."
    return "Happy to help with the DET request. Let's start with the basics."


def _has_captured_intake(intake: dict[str, Any]) -> bool:
    return any(
        bool(intake.get(field))
        for field in (
            "project_name",
            "terraform_repo",
            "team_channel",
            "workspace_mode",
            "workspace_names",
            "environments",
            "regions",
            "vpc_model",
            "service_name",
            "business_justification",
            "team_dl",
        )
    )


def _join_natural(values: list[str]) -> str:
    clean_values = [str(value).strip() for value in values if str(value).strip()]
    if len(clean_values) <= 1:
        return "".join(clean_values)
    if len(clean_values) == 2:
        return " and ".join(clean_values)
    return ", ".join(clean_values[:-1]) + ", and " + clean_values[-1]


def _deterministic_extract(text: str, current_intake: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    lower = text.lower()

    environments = [
        env
        for env in ALLOWED_ENVIRONMENTS
        if re.search(rf"\b{re.escape(env.lower())}\b", lower)
    ]
    if environments:
        updates["environments"] = environments

    regions = []
    for region in re.findall(r"\b[a-z]{2}-[a-z]+-\d\b", lower):
        if region not in regions:
            regions.append(region)
    if regions:
        updates["regions"] = regions

    for vpc_model in ALLOWED_VPC_MODELS:
        if re.search(rf"\b{re.escape(vpc_model.lower())}\b", lower):
            updates["vpc_model"] = vpc_model
            break

    email = re.search(r"\b[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+\b", text)
    if email:
        updates["team_dl"] = email.group(0)

    members = re.findall(r"<@([A-Z0-9]+)>", text)
    if members:
        updates["members"] = members

    terraform_repo = _extract_terraform_repo(text)
    if terraform_repo:
        updates["terraform_repo"] = terraform_repo

    team_channel = _extract_team_channel(text)
    if team_channel:
        updates["team_channel"] = team_channel
    workspace_mode = _extract_workspace_mode(text)
    if workspace_mode:
        updates["workspace_mode"] = workspace_mode
    workspace_names = _extract_workspace_names(text, current_intake)
    if workspace_names:
        updates["workspace_names"] = workspace_names

    project = _extract_labeled_value(text, labels=("project name", "workload name"))
    if not project:
        match = re.search(
            r"\b(?:project|workload)\s*(?:is|=|:|called|named)\s+"
            r"([A-Za-z0-9@._\-/ ]{2,80})",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            project = _trim_extracted_value(match.group(1), stop_at_sentence=True)
    if not project:
        match = re.search(r"\b([A-Za-z][A-Za-z0-9_-]{1,40})\s+project\b", text)
        if match:
            project = match.group(1)
    if not project:
        match = re.search(
            r"\bcreate\s+(?:a|an|the)?\s*"
            r"(?:(?:dev|qa|prod|and)\s+)*"
            r"([A-Za-z][A-Za-z0-9_-]{1,40})\b",
            text,
            flags=re.IGNORECASE,
        )
        if match and match.group(1).lower() not in {"project", "workload", "service"}:
            project = match.group(1)
    if project:
        updates["project_name"] = project

    service = _extract_labeled_value(text, labels=("service name", "service"))
    if service:
        updates["service_name"] = service

    justification = _extract_labeled_value(
        text,
        labels=("business justification", "justification", "because"),
        stop_at_sentence=False,
    )
    if justification:
        updates["business_justification"] = justification

    return updates


def _extract_labeled_value(
    text: str,
    *,
    labels: tuple[str, ...],
    stop_at_sentence: bool = True,
) -> str:
    for label in labels:
        pattern = (
            rf"\b{re.escape(label)}\b\s*(?:is|=|:|called|named)?\s+"
            r"([A-Za-z0-9@._\-/ ]{2,160})"
        )
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _trim_extracted_value(match.group(1), stop_at_sentence=stop_at_sentence)
    return ""


def _extract_terraform_repo(text: str) -> str:
    labeled = _extract_labeled_value(
        text,
        labels=("terraform repo", "terraform github repo", "github repo", "repo"),
        stop_at_sentence=True,
    )
    for candidate in (labeled, text):
        match = re.search(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b", candidate)
        if match:
            return match.group(1)
    return ""


def _extract_team_channel(text: str) -> str:
    match = re.search(r"<#([A-Z0-9]+)(?:\|([^>]+))?>", text)
    if match:
        # Prefer human-readable channel name from user input if Slack provides it.
        return (match.group(2) or "").strip() or match.group(1)
    named = re.search(r"(?:^|\s)#([a-z0-9][a-z0-9_-]{1,80})\b", text, flags=re.IGNORECASE)
    if named:
        return named.group(1)
    return _extract_labeled_value(
        text,
        labels=("team channel", "channel"),
        stop_at_sentence=True,
    )


def _extract_workspace_mode(text: str) -> str:
    lower = text.lower()
    if "default" in lower and "workspace" in lower:
        return "default"
    if any(word in lower for word in ("custom workspace", "custom name", "my own workspace")):
        return "custom"
    return ""


def _extract_workspace_names(text: str, current_intake: dict[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for env in ("dev", "qa", "prod"):
        match = re.search(
            rf"\b{env}\b\s*(?:=|:|name\s+is)\s*([A-Za-z0-9._-]+)",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            names[env.capitalize() if env != "prod" else "Prod"] = match.group(1).strip()
    if names:
        return names

    # Convenience: when only one environment is selected, accept a single custom name.
    selected_envs = list(current_intake.get("environments") or [])
    if len(selected_envs) == 1 and "custom" in text.lower():
        candidates = re.findall(r"\b([A-Za-z][A-Za-z0-9._-]{2,})\b", text)
        stop_words = {
            "i",
            "want",
            "custom",
            "name",
            "workspace",
            "for",
            "the",
            "with",
            "and",
            "dev",
            "qa",
            "prod",
        }
        usable = [value for value in candidates if value.lower() not in stop_words]
        if usable:
            names[selected_envs[0]] = usable[-1]
    return names


def _trim_extracted_value(value: str, *, stop_at_sentence: bool) -> str:
    raw = value.strip()
    stops = [",", ";", "\n", " with ", " team dl ", " env ", " environment "]
    if stop_at_sentence:
        stops.extend([".", " because ", " for "])
    lower = raw.lower()
    cut = len(raw)
    for stop in stops:
        index = lower.find(stop)
        if index >= 0:
            cut = min(cut, index)
    return raw[:cut].strip(" .,-")


def _llm_gateway_error_blocks(session_key: str, error_desc: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    ":warning: *Issue with LLM Gateway*\n"
                    # f"_{error_desc}_\n\n"
                    "The AI assistant is currently unavailable. "
                    "You can fill in the request using the form, or cancel."
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open Form"},
                    "style": "primary",
                    "action_id": "det_chat_open_form",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Cancel"},
                    "style": "danger",
                    "action_id": "det_chat_cancel",
                    "value": session_key,
                },
            ],
        },
    ]


def _approval_blocks(session_key: str, preview_text: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": _truncate_for_slack(preview_text),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "action_id": "det_chat_approve",
                    "value": session_key,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Cancel"},
                    "style": "danger",
                    "action_id": "det_chat_cancel",
                    "value": session_key,
                },
            ],
        },
    ]


def _plain_text_preview(preview: dict[str, Any]) -> str:
    request_id = preview.get("request_id") or "DET request"
    return f"Preview ready for {request_id}. Use the buttons to approve or cancel."



def _draft_text(intake: dict[str, Any]) -> str:
    normalized = normalize_intake(intake)
    lines = ["Current draft:"]
    for label, key in (
        ("Project", "project_name"),
        ("Service", "service_name"),
        ("Environments", "environments"),
        ("Regions", "regions"),
        ("VPC", "vpc_model"),
        ("Team DL", "team_dl"),
        ("Team Channel", "team_channel"),
        ("Workspace Mode", "workspace_mode"),
        ("Workspace Names", "workspace_names"),
        ("Business justification", "business_justification"),
    ):
        value = normalized.get(key)
        if isinstance(value, list):
            value = ", ".join(value)
        if value:
            lines.append(f"- {label}: `{value}`")
    if len(lines) == 1:
        lines.append("- No fields captured yet.")
    return "\n".join(lines)


def _intro_text() -> str:
    return (
        "Happy to help create the DET AWS  request. You can send everything in one or we can talk through it step by step.\n\n"
        "message, or we can fill it in step by step.\n\n"
        "Follow this <https://salesforce-sandbox2.enterprise.slack.com/docs/T04SR5XV56X/F0B2CDRBUBX|DOC for FAQ on Onboarding process>.\n\n"
        "To start, tell me the project/workload name, environment, and region.\n\n"
        "Example: `Create a Dev sample project in us-east-1, small VPC, service EMS API, team channel ems-team, github repo adityajhacse/test, "
        "team DL ems-team@example.com because this is for a new workload.`"
    )


def _strip_bot_mentions(text: str) -> str:
    return re.sub(r"<@[A-Z0-9]+>", "", text or "").strip()


def _is_reset(text: str) -> bool:
    return text.lower() in {"reset", "cancel", "start over", "restart"}


def _dry_run_enabled() -> bool:
    raw = os.environ.get("DET_DRY_RUN", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _truncate_for_slack(text: str, limit: int = 2900) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n... truncated ..."
