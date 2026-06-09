from __future__ import annotations

import json
import re
from typing import Any

from github_api import build_github_intake_document, sanitize_git_branch_from_project_name


ALLOWED_ENVIRONMENTS = ("Dev", "QA", "Prod")
ALLOWED_REGIONS = ("us-east-1", "us-west-2", "eu-west-1")
ALLOWED_VPC_MODELS = ("Big", "Medium", "Small")
REQUIRED_FIELDS = (
    "project_name",
    "terraform_repo",
    "team_channel",
    "environments",
    "regions",
    "vpc_model",
    "service_name",
    "business_justification",
    "team_dl",
)
WORKSPACE_MODES = ("default", "custom")

 
def intake_schema() -> dict[str, Any]:
    return {
        "required_fields": list(REQUIRED_FIELDS),
        "optional_fields": ["members"],
        "allowed_values": {
            "environments": list(ALLOWED_ENVIRONMENTS),
            "regions": list(ALLOWED_REGIONS),
            "vpc_model": list(ALLOWED_VPC_MODELS),
            "workspace_mode": list(WORKSPACE_MODES),
        },
        "examples": {
            "chat_message": (
                "Create a Dev and QA EMS project in us-east-1, small VPC, "
                "service EMS API, team DL ems-team@example.com because the "
                "team needs onboarding for a new workload."
            ),
            "intake": {
                "project_name": "EMS",
                "terraform_repo": "adityajhacse/test",
                "team_channel": "C0123456789",
                "workspace_mode": "default",
                "workspace_names": {"Dev": "ems-dev", "QA": "ems-qa"},
                "environments": ["Dev", "QA"],
                "regions": ["us-east-1"],
                "vpc_model": "Small",
                "service_name": "EMS API",
                "business_justification": "Onboarding a new workload.",
                "members": [],
                "team_dl": "ems-team@example.com",
            },
        },
    }


def normalize_intake(candidate: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(candidate) if isinstance(candidate, dict) else {}
    project_name = _clean_text(raw.get("project_name"))

    normalized = {
        "project_name": project_name,
        "project_slug": _slugify_project_name(project_name),
        "project_upper": _project_upper(project_name),
        "terraform_repo": _normalize_repo(raw.get("terraform_repo")),
        "team_channel": _normalize_channel(raw.get("team_channel")),
        "workspace_mode": _normalize_workspace_mode(raw.get("workspace_mode")),
        "environments": _normalize_list(raw.get("environments"), ALLOWED_ENVIRONMENTS),
        "regions": _normalize_list(raw.get("regions"), ALLOWED_REGIONS),
        "vpc_model": _normalize_scalar(raw.get("vpc_model"), ALLOWED_VPC_MODELS),
        "service_name": _clean_text(raw.get("service_name")),
        "business_justification": _clean_text(raw.get("business_justification")),
        "members": _normalize_members(raw.get("members")),
        "team_dl": _normalize_email(raw.get("team_dl")),
        "workspace_names": _normalize_workspace_names(raw.get("workspace_names")),
    }
    return normalized


def validate_intake(candidate: dict[str, Any] | None) -> dict[str, Any]:
    normalized = normalize_intake(candidate)
    missing_fields = []
    errors = []

    for field in REQUIRED_FIELDS:
        value = normalized.get(field)
        if isinstance(value, list):
            if not value:
                missing_fields.append(field)
        elif not value:
            missing_fields.append(field)

    if normalized.get("environments") and not normalized.get("workspace_mode"):
        missing_fields.append("workspace_mode")
    if normalized.get("workspace_mode") == "custom":
        workspace_names = normalized.get("workspace_names")
        if not isinstance(workspace_names, dict):
            workspace_names = {}
        missing_workspace_envs = [
            env for env in normalized.get("environments", []) if not workspace_names.get(env)
        ]
        if missing_workspace_envs:
            missing_fields.append("workspace_names")

    _add_unknown_values_errors(candidate or {}, errors)

    team_dl = normalized.get("team_dl", "")
    if team_dl and not _looks_like_email(team_dl):
        errors.append("team_dl should be an email-like distribution list.")
    terraform_repo = normalized.get("terraform_repo", "")
    if terraform_repo and not _looks_like_repo(terraform_repo):
        errors.append("terraform_repo should look like owner/repository.")

    return {
        "valid": not missing_fields and not errors,
        "missing_fields": missing_fields,
        "errors": errors,
        "intake": normalized,
    }


def preview_request(
    candidate: dict[str, Any] | None,
    slack_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validate_intake(candidate)
    intake = validation["intake"]
    dns_values = _private_dns_values(intake)
    workspaces = _workspace_names(intake)

    github_path = ""
    aft_payload: dict[str, Any] | None = None
    request_id = ""
    if validation["valid"]:
        github_path, aft_payload = build_github_intake_document(intake, slack_user or {})
        request_id = str(aft_payload.get("request_id", ""))

    return {
        "valid": validation["valid"],
        "missing_fields": validation["missing_fields"],
        "errors": validation["errors"],
        "intake": intake,
        "request_id": request_id,
        "github_path": github_path,
        "github_branch": sanitize_git_branch_from_project_name(
            intake.get("project_name") or intake.get("project_slug") or "intake"
        ),
        "hcp_project": intake.get("project_upper", ""),
        "workspaces": workspaces,
        "private_dns": dns_values,
        "aft_json": aft_payload,
        "slack_preview": _slack_preview_text(
            intake,
            request_id=request_id,
            github_path=github_path,
            workspaces=workspaces,
            dns_values=dns_values,
        ),
    }


def merge_intake_updates(
    current: dict[str, Any] | None,
    updates: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(current or {})
    for key, value in (updates or {}).items():
        if key not in {
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
            "members",
            "team_dl",
        }:
            continue
        if value in (None, ""):
            continue
        if isinstance(value, list) and not value:
            continue
        if key == "team_channel":
            existing = str(merged.get("team_channel") or "").strip()
            incoming = str(value).strip()
            # Keep a human-friendly channel name once captured; do not downgrade to raw Slack ID.
            if existing and not _looks_like_slack_channel_id(existing) and _looks_like_slack_channel_id(incoming):
                continue
        merged[key] = value
    return normalize_intake(merged)


def format_missing_fields(missing_fields: list[str]) -> str:
    labels = {
        "project_name": "project/workload name",
        "terraform_repo": "Terraform GitHub repository (org/repo)",
        "team_channel": "team channel",
        "workspace_mode": "workspace naming mode (default/custom)",
        "workspace_names": "custom workspace names for each environment",
        "environments": "environment(s): Dev, QA, or Prod",
        "regions": "region(s): us-east-1, us-west-2, or eu-west-1",
        "vpc_model": "VPC size: Big, Medium, or Small",
        "service_name": "service name",
        "business_justification": "business justification",
        "team_dl": "team distribution list email",
    }
    return ", ".join(labels.get(field, field) for field in missing_fields)


def _normalize_list(value: Any, allowed_values: tuple[str, ...]) -> list[str]:
    values = value if isinstance(value, list) else [value]
    normalized = []
    for item in values:
        for candidate in _expand_multi_values(item):
            match = _normalize_scalar(candidate, allowed_values)
            if match and match not in normalized:
                normalized.append(match)
    return normalized


def _normalize_scalar(value: Any, allowed_values: tuple[str, ...]) -> str:
    if value is None:
        return ""
    raw = str(value).strip()
    for allowed in allowed_values:
        if raw.lower() == allowed.lower():
            return allowed
    return ""


def _normalize_members(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    members = []
    for item in value:
        raw = str(item).strip()
        match = re.search(r"<@([A-Z0-9]+)>", raw)
        if match:
            raw = match.group(1)
        if raw and raw not in members:
            members.append(raw)
    return members


def _add_unknown_values_errors(candidate: dict[str, Any], errors: list[str]) -> None:
    for field, allowed in (
        ("environments", ALLOWED_ENVIRONMENTS),
        ("regions", ALLOWED_REGIONS),
    ):
        raw_values = candidate.get(field) or []
        if not isinstance(raw_values, list):
            raw_values = [raw_values]
        unknown = [
            str(value)
            for value in raw_values
            for expanded in _expand_multi_values(value)
            if expanded and not _normalize_scalar(expanded, allowed)
        ]
        if unknown:
            errors.append(
                f"{field} contains unsupported value(s): {', '.join(unknown)}."
            )

    raw_vpc = candidate.get("vpc_model")
    if raw_vpc and not _normalize_scalar(raw_vpc, ALLOWED_VPC_MODELS):
        errors.append(
            "vpc_model must be one of: "
            + ", ".join(ALLOWED_VPC_MODELS)
            + "."
        )


def _expand_multi_values(value: Any) -> list[str]:
    if value is None:
        return []
    raw = str(value).strip()
    if not raw:
        return []
    # Accept input like "Dev, Prod" or "Dev and Prod".
    parts = [part.strip() for part in re.split(r",|/|\band\b", raw, flags=re.IGNORECASE)]
    cleaned = [part for part in parts if part]
    return cleaned or [raw]


def _private_dns_values(intake: dict[str, Any]) -> list[dict[str, str]]:
    values = []
    slug = intake.get("project_slug", "")
    for environment in intake.get("environments", []):
        for region in intake.get("regions", []):
            values.append(
                {
                    "environment": environment,
                    "region": region,
                    "value": _private_dns_value(slug, environment, region),
                }
            )
    return values


def _workspace_names(intake: dict[str, Any]) -> list[dict[str, str]]:
    project_slug = intake.get("project_slug", "")
    custom_names = intake.get("workspace_names")
    if not isinstance(custom_names, dict):
        custom_names = {}
    return [
        {
            "environment": environment,
            "workspace": custom_names.get(environment) or _workspace_name(project_slug, environment),
        }
        for environment in intake.get("environments", [])
    ]


def _private_dns_value(project_slug: str, environment: str, region: str) -> str:
    if environment == "Prod":
        prefix = project_slug
    else:
        prefix = f"{project_slug}-{environment.lower()}"
    return f"{prefix}.{region}.internal.det.salesforce.com"


def _workspace_name(project_slug: str, environment: str) -> str:
    return f"{project_slug}-{environment.lower()}"


def _slack_preview_text(
    intake: dict[str, Any],
    *,
    request_id: str,
    github_path: str,
    workspaces: list[dict[str, str]],
    dns_values: list[dict[str, str]],
) -> str:
    workspace_lines = "\n".join(
        f"- {item['environment']}: `{item['workspace']}`" for item in workspaces
    ) or "-"
    dns_lines = "\n".join(
        f"- {item['environment']} / {item['region']}: `{item['value']}`"
        for item in dns_values
    ) or "-"

    return (
        "*DET chatbot request preview*\n"
        f"*Request ID:* `{request_id}`\n"
        f"*Project:* `{intake.get('project_name', '')}` "
        f"(`{intake.get('project_upper', '')}`)\n"
        f"*Terraform repo:* `{intake.get('terraform_repo', '')}`\n"
        f"*Team channel:* {_display_team_channel(intake.get('team_channel', ''))}\n"
        f"*Workspace mode:* `{intake.get('workspace_mode', '')}`\n"
        f"*Service:* `{intake.get('service_name', '')}`\n"
        f"*Environment(s):* `{', '.join(intake.get('environments', []))}`\n"
        f"*Region(s):* `{', '.join(intake.get('regions', []))}`\n"
        f"*VPC:* `{intake.get('vpc_model', '')}`\n"
        f"*Team DL:* `{intake.get('team_dl', '')}`\n"
        f"*Business justification:* {intake.get('business_justification', '')}\n"
        f"*GitHub request path:* `{github_path}`\n"
        "*HCP workspaces:*\n"
        f"{workspace_lines}\n"
        "*Private DNS:*\n"
        f"{dns_lines}"
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _slugify_project_name(project_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", project_name.strip().lower())
    return normalized.strip("-")


def _project_upper(project_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", project_name.strip()).strip("-")
    return cleaned.upper()


def _normalize_repo(value: Any) -> str:
    raw = _clean_text(value)
    raw = re.sub(r"^https?://github\.com/", "", raw, flags=re.IGNORECASE)
    raw = raw.strip("/")
    if raw.endswith(".git"):
        raw = raw[:-4]
    return raw


def _looks_like_repo(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value))


def _normalize_channel(value: Any) -> str:
    raw = _clean_text(value)
    hashtag = re.search(r"(?:^|\s)#([a-z0-9][a-z0-9_-]{1,80})\b", raw, flags=re.IGNORECASE)
    if hashtag:
        return hashtag.group(1)
    match = re.search(r"<#([A-Z0-9]+)(?:\|([^>]+))?>", raw)
    if match:
        # Keep the friendly channel name when available.
        return (match.group(2) or "").strip() or match.group(1)
    return raw


def _looks_like_slack_channel_id(value: str) -> bool:
    return bool(re.fullmatch(r"[CG][A-Z0-9]{8,}", value.strip().upper()))


def _normalize_workspace_mode(value: Any) -> str:
    raw = _clean_text(value).lower()
    if raw in WORKSPACE_MODES:
        return raw
    return ""


def _normalize_workspace_names(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str] = {}
    for env, name in value.items():
        env_name = _normalize_scalar(env, ALLOWED_ENVIRONMENTS)
        workspace_name = _clean_text(name)
        if env_name and workspace_name:
            normalized[env_name] = workspace_name
    return normalized


def _looks_like_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))


def _normalize_email(value: Any) -> str:
    raw = _clean_text(value).strip(" ,;.")
    if not raw:
        return ""
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", raw)
    if match:
        return match.group(0).strip(" ,;.")
    return raw


def _display_team_channel(value: Any) -> str:
    raw = _clean_text(value)
    if not raw:
        return "`-`"
    if _looks_like_slack_channel_id(raw):
        return f"<#{raw}>"
    if raw.startswith("#"):
        return f"`{raw}`"
    return f"`#{raw}`"


def to_pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True)
