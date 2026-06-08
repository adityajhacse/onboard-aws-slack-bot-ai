import json
import logging
import os
import ssl
from typing import Any
from urllib import error, request

import certifi


class HcpTerraformError(Exception):
    pass


def _ssl_context():
    """Use certifi CA bundle only for HCP requests."""
    return ssl.create_default_context(cafile=certifi.where())


def create_project_with_workspaces(
    *,
    project_name: str,
    project_slug: str,
    environments: list[str],
    terraform_repo: str,
    workspace_names: dict[str, str] | None = None,
) -> dict:
    token, organization, base_url = _hcp_config()
    project = _create_project(
        project_name=project_name,
        token=token,
        organization=organization,
        base_url=base_url,
    )
    project_id = project["id"]
    workspace_names = []

    for environment in environments:
        environment_slug = environment.strip().lower()
        workspace_name = _resolve_workspace_name(
            project_slug=project_slug,
            environment=environment,
            workspace_names=workspace_names or {},
        )
        workspace = _create_workspace(
            workspace_name=workspace_name,
            environment_slug=environment_slug,
            project_id=project_id,
            terraform_repo=terraform_repo,
            token=token,
            organization=organization,
            base_url=base_url,
        )
        _set_workspace_env_vars(
            workspace_id=workspace["id"],
            token=token,
            base_url=base_url,
        )
        workspace_names.append(workspace_name)

    return {"project_name": project["name"], "workspace_names": workspace_names}


def create_project(project_name):
    token, organization, base_url = _hcp_config()
    project = _create_project(
        project_name=project_name,
        token=token,
        organization=organization,
        base_url=base_url,
    )
    return project["name"]


def _hcp_config() -> tuple[str, str, str]:
    token = os.environ.get("HCP_TERRAFORM_TOKEN", "").strip()
    organization = os.environ.get("HCP_TERRAFORM_ORG", "").strip()
    base_url = os.environ.get("HCP_TERRAFORM_URL", "https://app.terraform.io").strip()
    if not token:
        raise HcpTerraformError("Missing HCP_TERRAFORM_TOKEN environment variable.")
    if not organization:
        raise HcpTerraformError("Missing HCP_TERRAFORM_ORG environment variable.")
    return token, organization, base_url


def _create_project(*, project_name: str, token: str, organization: str, base_url: str) -> dict:
    payload = {"data": {"type": "projects", "attributes": {"name": project_name}}}
    parsed = _post(
        url=f"{base_url}/api/v2/organizations/{organization}/projects",
        payload=payload,
        token=token,
    )
    try:
        return {"id": parsed["data"]["id"], "name": parsed["data"]["attributes"]["name"]}
    except (KeyError, json.JSONDecodeError) as exc:
        raise HcpTerraformError("HCP Terraform returned an unexpected response.") from exc


def _create_workspace(
    *,
    workspace_name: str,
    environment_slug: str,
    project_id: str,
    terraform_repo: str,
    token: str,
    organization: str,
    base_url: str,
) -> dict:
    _ensure_workspace_branch(terraform_repo, environment_slug)
    vcs_repo = _build_vcs_repo(terraform_repo, environment_slug)
    payload = {
        "data": {
            "type": "workspaces",
            "attributes": {
                "name": workspace_name,
                "vcs-repo": vcs_repo,
            },
            "relationships": {
                "project": {"data": {"id": project_id, "type": "projects"}},
            },
        }
    }
    parsed = _post(
        url=f"{base_url}/api/v2/organizations/{organization}/workspaces",
        payload=payload,
        token=token,
    )
    try:
        return {"id": parsed["data"]["id"], "name": parsed["data"]["attributes"]["name"]}
    except (KeyError, json.JSONDecodeError) as exc:
        raise HcpTerraformError("HCP Terraform workspace response was unexpected.") from exc


def _ensure_workspace_branch(terraform_repo: str, environment_slug: str) -> None:
    raw = os.environ.get("HCP_TERRAFORM_AUTO_CREATE_BRANCH", "true").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return

    owner, repo = _parse_repository(terraform_repo)
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise HcpTerraformError(
            "Missing GITHUB_TOKEN. Required to create missing Terraform branches "
            f"for workspace VCS mapping (`{owner}/{repo}` -> `{environment_slug}`)."
        )

    base_branch = (
        os.environ.get("HCP_TERRAFORM_REPO_BASE_BRANCH", "").strip()
        or os.environ.get("GITHUB_BASE_BRANCH", "").strip()
        or "main"
    )
    try:
        from github_api import GitHubApiError, ensure_git_branch

        ensure_git_branch(owner, repo, environment_slug, base_branch, token)
    except Exception as exc:
        if exc.__class__.__name__ == "GitHubApiError":
            raise HcpTerraformError(
                "Failed to ensure Terraform repo branch "
                f"`{environment_slug}` exists in `{owner}/{repo}`: {exc}"
            ) from exc
        logging.exception("Unexpected error while ensuring Terraform branch exists.")
        raise HcpTerraformError(
            f"Unexpected error creating Terraform branch `{environment_slug}` in `{owner}/{repo}`."
        ) from exc


def _parse_repository(terraform_repo: str) -> tuple[str, str]:
    value = terraform_repo.strip().strip("/")
    if value.endswith(".git"):
        value = value[:-4]
    if value.startswith("https://github.com/"):
        value = value.removeprefix("https://github.com/")
    if value.startswith("http://github.com/"):
        value = value.removeprefix("http://github.com/")
    parts = value.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HcpTerraformError(
            f"Invalid terraform_repo `{terraform_repo}`. Expected `owner/repo`."
        )
    return parts[0], parts[1]


def _build_vcs_repo(terraform_repo: str, environment_slug: str) -> dict:
    oauth_token_id = os.environ.get("HCP_TERRAFORM_VCS_OAUTH_TOKEN_ID", "").strip()
    github_app_installation_id = os.environ.get(
        "HCP_TERRAFORM_GITHUB_APP_INSTALLATION_ID",
        "",
    ).strip()
    if not oauth_token_id and not github_app_installation_id:
        raise HcpTerraformError(
            "Missing VCS linkage config. Set HCP_TERRAFORM_VCS_OAUTH_TOKEN_ID "
            "or HCP_TERRAFORM_GITHUB_APP_INSTALLATION_ID so Terraform workspaces "
            "can connect to the GitHub repository."
        )

    vcs_repo = {"identifier": terraform_repo, "branch": environment_slug}
    if oauth_token_id:
        vcs_repo["oauth-token-id"] = oauth_token_id
    if github_app_installation_id:
        vcs_repo["github-app-installation-id"] = github_app_installation_id
    return vcs_repo


def _set_workspace_env_vars(*, workspace_id: str, token: str, base_url: str) -> None:
    role_arn = os.environ.get(
        "HCP_TFC_AWS_RUN_ROLE_ARN",
        "arn:aws:iam::916657620953:role/HCP-terraform-role",
    ).strip()
    _create_workspace_var(
        workspace_id=workspace_id,
        key="TFC_AWS_PROVIDER_AUTH",
        value="true",
        token=token,
        base_url=base_url,
    )
    _create_workspace_var(
        workspace_id=workspace_id,
        key="TFC_AWS_RUN_ROLE_ARN",
        value=role_arn,
        token=token,
        base_url=base_url,
    )


def _create_workspace_var(
    *,
    workspace_id: str,
    key: str,
    value: str,
    token: str,
    base_url: str,
) -> None:
    payload = {
        "data": {
            "type": "vars",
            "attributes": {
                "key": key,
                "value": value,
                "category": "env",
                "hcl": False,
                "sensitive": False,
            },
        }
    }
    _post(
        url=f"{base_url}/api/v2/workspaces/{workspace_id}/vars",
        payload=payload,
        token=token,
    )


def _workspace_name(project_slug: str, environment_slug: str) -> str:
    return f"{project_slug}-{environment_slug}"


def _resolve_workspace_name(
    *,
    project_slug: str,
    environment: str,
    workspace_names: dict[str, str] | list[Any] | str | None,
) -> str:
    workspace_map = workspace_names if isinstance(workspace_names, dict) else {}
    custom_name = str(workspace_map.get(environment) or "").strip()
    if custom_name:
        return custom_name
    return _workspace_name(project_slug, environment.strip().lower())


def _post(*, url: str, payload: dict, token: str) -> dict:
    req = request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30, context=_ssl_context()) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HcpTerraformError(_build_http_error_message(exc.code, detail)) from exc
    except error.URLError as exc:
        raise HcpTerraformError(f"Network error while calling HCP Terraform: {exc.reason}") from exc

    try:
        return json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise HcpTerraformError("HCP Terraform returned a non-JSON response.") from exc


def _build_http_error_message(status_code, response_body):
    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError:
        return f"HCP Terraform API returned HTTP {status_code}."

    errors = parsed.get("errors") or []
    if errors:
        title = errors[0].get("title") or "API error"
        detail = errors[0].get("detail")
        if detail:
            return f"HCP Terraform API returned HTTP {status_code}: {title} - {detail}"
        return f"HCP Terraform API returned HTTP {status_code}: {title}"
    return f"HCP Terraform API returned HTTP {status_code}."
