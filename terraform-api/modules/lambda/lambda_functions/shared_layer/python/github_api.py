"""
Create or update a file in a GitHub repository via the Contents API.

Requires GITHUB_TOKEN (repo scope for private repos; public repo still needs a token to push).
https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28#create-or-update-file-contents
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import ssl
from pathlib import Path
from typing import Any
from urllib import error, request

import certifi

class GitHubApiError(Exception):
    pass


# AFT Control Tower defaults (edit here; not read from .env)
AFT_ACCOUNT_EMAIL = "abc@example.com"
AFT_MANAGED_OU_BY_ENV: dict[str, str] = {
    "Dev": "Dev (ou-1234567890)",
    "QA": "QA (ou-1234567890)",
    "Prod": "Prod (ou-1234567890)",
}
AFT_SSO_USER_EMAIL_DEFAULT = "aditya.jha@salesforce.com"
AFT_SSO_USER_FIRST_NAME_DEFAULT = "Aditya"
AFT_SSO_USER_LAST_NAME_DEFAULT = "jha"

def _ssl_context():
    """Use certifi CA bundle only for HCP requests."""
    return ssl.create_default_context(cafile=certifi.where())



def _github_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    """Return (HTTP status, parsed JSON body). Does not raise on 4xx/5xx."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "aws-det-poc-slack",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=60, context=_ssl_context()) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return resp.status, None
            return resp.status, json.loads(raw)
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"message": raw or str(exc)}
        return exc.code, parsed


def sanitize_git_branch_from_project_name(name: str) -> str:
    """
    Turn intake *project name* (or slug fallback) into a valid Git branch segment.
    """
    raw = (name or "").strip()
    if not raw:
        raw = "intake"
    s = re.sub(r"[^0-9A-Za-z._/-]+", "-", raw)
    s = re.sub(r"-+", "-", s).strip("-./")
    s = s.lstrip("-")
    if not s:
        s = "intake"
    if len(s) > 200:
        s = s[:200].rstrip("-")
    return s


def get_branch_tip_sha(owner: str, repo: str, branch: str, token: str) -> str:
    """Resolve ``branch`` tip commit SHA (e.g. ``main``)."""
    from urllib.parse import quote

    ref = f"heads/{branch}"
    url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/{quote(ref)}"
    status, body = _github_request("GET", url, token)
    if status != 200 or not isinstance(body, dict):
        raise GitHubApiError(f"Could not resolve branch {branch!r} (HTTP {status}): {body}")
    obj = body.get("object") or {}
    sha = obj.get("sha") or ""
    if not sha:
        raise GitHubApiError(f"Missing SHA for branch {branch!r}.")
    return sha


def get_repo_default_branch(owner: str, repo: str, token: str) -> str:
    """Read repository default branch (e.g. main/master)."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    status, body = _github_request("GET", url, token)
    if status != 200 or not isinstance(body, dict):
        raise GitHubApiError(f"Could not load repository metadata (HTTP {status}): {body}")
    default_branch = str(body.get("default_branch") or "").strip()
    if not default_branch:
        raise GitHubApiError("Repository default branch is not set.")
    return default_branch


def ensure_git_branch(
    owner: str,
    repo: str,
    new_branch: str,
    base_branch: str,
    token: str,
) -> None:
    """
    Create ``refs/heads/{new_branch}`` at the same commit as ``base_branch`` if it does not exist.
    https://docs.github.com/en/rest/git/refs?apiVersion=2022-11-28#create-a-reference
    """
    from urllib.parse import quote

    ref_new = f"heads/{new_branch}"
    url_get = f"https://api.github.com/repos/{owner}/{repo}/git/ref/{quote(ref_new)}"
    status, _ = _github_request("GET", url_get, token)
    if status == 200:
        return

    try:
        base_sha = get_branch_tip_sha(owner, repo, base_branch, token)
    except GitHubApiError as exc:
        # If configured base branch doesn't exist, use repository default branch.
        message = str(exc)
        if f"branch {base_branch!r}" not in message:
            raise
        fallback_branch = get_repo_default_branch(owner, repo, token)
        base_sha = get_branch_tip_sha(owner, repo, fallback_branch, token)
    url_post = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
    payload = {"ref": f"refs/heads/{new_branch}", "sha": base_sha}
    status, body = _github_request("POST", url_post, token, payload)
    if status in (201, 200):
        return
    if status == 422 and isinstance(body, dict):
        msg = str(body.get("message", "")).lower()
        if "already exists" in msg:
            return
    raise GitHubApiError(f"Could not create branch {new_branch!r} (HTTP {status}): {body}")


def _get_file_sha(owner: str, repo: str, path: str, branch: str, token: str) -> str | None:
    from urllib.parse import quote

    encoded = quote(path, safe="/")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded}?ref={branch}"
    status, body = _github_request("GET", url, token)
    if status == 404:
        return None
    if status != 200 or not isinstance(body, dict):
        msg = body.get("message", str(body)) if isinstance(body, dict) else str(body)
        raise GitHubApiError(f"Could not read path metadata (HTTP {status}): {msg}")
    return body.get("sha")


def put_repository_json_file(
    owner: str,
    repo: str,
    path: str,
    data: dict[str, Any],
    commit_message: str,
    *,
    token: str | None = None,
    branch: str = "main",
) -> dict[str, Any]:
    """
    Create or update a JSON file at ``path`` on ``branch``.
    Returns the JSON body from GitHub's successful PUT response (includes ``content`` metadata).
    """
    token = (token or os.environ.get("GITHUB_TOKEN", "")).strip()
    if not token:
        raise GitHubApiError("Missing GITHUB_TOKEN environment variable.")

    text = json.dumps(data, indent=2) + "\n"
    content_b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")

    from urllib.parse import quote

    encoded = quote(path, safe="/")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded}"

    body: dict[str, Any] = {
        "message": commit_message,
        "content": content_b64,
        "branch": branch,
    }
    existing_sha = _get_file_sha(owner, repo, path, branch, token)
    if existing_sha:
        body["sha"] = existing_sha

    status, response = _github_request("PUT", url, token, body)
    if status not in (200, 201) or not isinstance(response, dict):
        msg = response.get("message", str(response)) if isinstance(response, dict) else str(response)
        raise GitHubApiError(f"PUT contents failed (HTTP {status}): {msg}")
    return response


def list_org_repositories(
    owner: str,
    token: str,
    *,
    query: str = "",
    limit: int = 100,
) -> list[str]:
    """Return full repo names from a GitHub org/user (e.g. owner/repo)."""
    from urllib.parse import quote

    owner = (owner or "").strip()
    if not owner:
        return []

    org_url = (
        "https://api.github.com/orgs/"
        f"{quote(owner)}/repos?per_page=100&type=all&sort=full_name&direction=asc"
    )
    status, body = _github_request("GET", org_url, token)
    if status == 404:
        # Owner may be a user account; fall back to user repositories endpoint.
        user_url = (
            "https://api.github.com/users/"
            f"{quote(owner)}/repos?per_page=100&type=owner&sort=full_name&direction=asc"
        )
        status, body = _github_request("GET", user_url, token)
    if status != 200 or not isinstance(body, list):
        raise GitHubApiError(
            f"Could not list repositories for owner {owner!r} (HTTP {status}): {body}"
        )

    q = (query or "").strip().lower()
    repos: list[str] = []
    for item in body:
        if not isinstance(item, dict):
            continue
        full_name = str(item.get("full_name") or "").strip()
        name = str(item.get("name") or "").strip()
        if not full_name or "/" not in full_name:
            continue
        if q and q not in full_name.lower() and q not in name.lower():
            continue
        repos.append(full_name)
        if len(repos) >= max(1, limit):
            break
    return repos


def _primary_environment(envs: list[str]) -> str:
    order = {"Dev": 0, "QA": 1, "Prod": 2}
    if not envs:
        return "Dev"
    return sorted(envs, key=lambda e: order.get(e, 99))[0]


def _env_suffix(env: str) -> str:
    return {"Dev": "dev", "QA": "qa", "Prod": "prod"}.get(env, env.lower().replace(" ", ""))


def _managed_ou_for_env(primary_env: str) -> str:
    return AFT_MANAGED_OU_BY_ENV.get(primary_env, AFT_MANAGED_OU_BY_ENV["Dev"])


def _github_actions_patterns() -> list[str]:
    raw = os.environ.get("AFT_GITHUB_ACTIONS_SUBJECT_PATTERNS", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            return list(parsed) if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return [
        "repo:SF-BT-NonProd/edd-platform-aws-sample-lambda:ref:refs/heads/main",
    ]


def build_github_intake_document(
    intake: dict[str, Any],
    slack_user: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    Build JSON for the repo in the same shape as ``src/sample.json``:

    ``{ "request_id": "...", "aft": { control_tower_parameters, custom_fields, change_management_parameters } }``

    ``intake`` is the dict returned by ``modal_lib.extract_intake_submission``.
    """
    slug = (intake.get("project_slug") or "det-intake").strip() or "det-intake"
    regions = list(intake.get("regions") or [])
    envs = list(intake.get("environments") or [])
    primary_env = _primary_environment(envs)
    env_key = _env_suffix(primary_env)
    primary_region = regions[0] if regions else "us-east-1"
    vpc = (intake.get("vpc_model") or "").strip().lower() or "small"
    justification = (intake.get("business_justification") or "").strip()
    project_display = (intake.get("project_name") or slug).strip()

    submitter = (
        slack_user.get("name")
        or slack_user.get("username")
        or slack_user.get("id")
        or "unknown"
    )
    team_dl = (intake.get("team_dl") or "").strip()
    sso_email = team_dl if "@" in team_dl else AFT_SSO_USER_EMAIL_DEFAULT

    request_id = f"{slug}-{env_key}"
    account_email = AFT_ACCOUNT_EMAIL
    account_name = os.environ.get(
        "AFT_ACCOUNT_NAME",
        f"{project_display} {primary_env}",
    )

    payload: dict[str, Any] = {
        "request_id": request_id,
        "aft": {
            "control_tower_parameters": {
                "AccountEmail": account_email,
                "AccountName": account_name,
                "ManagedOrganizationalUnit": _managed_ou_for_env(primary_env),
                "SSOUserEmail": sso_email,
                "SSOUserFirstName": AFT_SSO_USER_FIRST_NAME_DEFAULT,
                "SSOUserLastName": AFT_SSO_USER_LAST_NAME_DEFAULT,
            },
            "custom_fields": {
                "github_actions_subject_patterns": _github_actions_patterns(),
                "enable_private_dns_rfc": True,
                "project_name": slug,
                "terraform_cloud_project": project_display,
                "region": primary_region,
                "vpc_size": vpc,
            },
            "change_management_parameters": {
                "change_requested_by": submitter,
                "change_reason": justification[:2000] if justification else "E2E",
            },
        },
    }

    default_path = f"requests/{request_id}.json"
    return default_path, payload


def github_process(
    full_intake: dict[str, Any] | None,
    user: dict[str, Any],
    channel_id: str,
    client: Any,
) -> None:
    """
    If ``GITHUB_TOKEN`` and ``full_intake`` are set, build the intake document, ensure
    a project branch, and commit JSON to the repo. On :exc:`GitHubApiError`, post an
    ephemeral Slack message. Logs and returns on other conditions without raising.
    """
    if os.environ.get("GITHUB_TOKEN", "").strip() and full_intake:
        try:
            default_path, payload = build_github_intake_document(full_intake, user)
            path = os.environ.get("GITHUB_FILE_PATH", "").strip() or default_path
            owner = os.environ.get("GITHUB_OWNER", "adityajhacse").strip()
            repo = os.environ.get("GITHUB_REPO", "test").strip()
            token = os.environ.get("GITHUB_TOKEN", "").strip()
            base_branch = os.environ.get("GITHUB_BASE_BRANCH", "main").strip()
            project_branch = sanitize_git_branch_from_project_name(
                full_intake.get("project_name") or full_intake.get("project_slug") or "intake"
            )
            ensure_git_branch(owner, repo, project_branch, base_branch, token)
            result = put_repository_json_file(
                owner,
                repo,
                path,
                payload,
                commit_message=f"DET intake {payload['request_id']}",
                token=token,
                branch=project_branch,
            )
            url = (result.get("content") or {}).get("html_url", "")
            logging.info("GitHub intake committed: %s", url or path)
        except GitHubApiError:
            logging.exception("GitHub upload failed after summary submit.")
        except Exception:
            logging.exception("Unexpected error during GitHub upload.")
    elif not os.environ.get("GITHUB_TOKEN", "").strip():
        logging.warning("GITHUB_TOKEN not set; skipping GitHub upload on summary submit.")
    elif full_intake is None:
        logging.warning(
            "No pending full intake for this user; GitHub skipped. "
            "Submit the intake form in the same session before confirming the summary."
        )


# --- Example payload & one-shot CLI ---

SAMPLE_DET_REQUEST: dict[str, Any] = {
    "request_id": "det-aws-platform-e2e-dev",
    "aft": {
        "control_tower_parameters": {
            "AccountEmail": "det-aws-platform-e2e-dev@salesforce.com",
            "AccountName": "DET AWS Platform e2e Dev",
            "ManagedOrganizationalUnit": "Dev (ou-fefj-m2v0wwkm)",
            "SSOUserEmail": "siva.eiplocalbb@salesforce.com",
            "SSOUserFirstName": "Kyrylo",
            "SSOUserLastName": "Ushkalov",
        },
        "custom_fields": {
            "github_actions_subject_patterns": [
                "repo:SF-BT-NonProd/edd-platform-aws-sample-lambda:ref:refs/heads/main"
            ],
            "enable_private_dns_rfc": True,
            "project_name": "det-aws-platform-e2e",
            "terraform_cloud_project": "DET AWS Platform e2e",
            "region": "us-east-1",
            "vpc_size": "small",
        },
        "change_management_parameters": {
            "change_requested_by": "Kyrylo Ushkalov",
            "change_reason": "E2E",
        },
    },
}
