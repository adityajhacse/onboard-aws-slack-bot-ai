from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from det_intake import intake_schema, normalize_intake, preview_request, validate_intake
from github_api import (
    build_github_intake_document,
    ensure_git_branch,
    put_repository_json_file,
    sanitize_git_branch_from_project_name,
)
from hcp_terraform import create_project_with_workspaces


mcp = FastMCP("aws-det-poc")


@mcp.resource("det://schema/intake")
def det_schema_resource() -> str:
    return json.dumps(intake_schema(), indent=2) 


@mcp.resource("det://examples/aft-request")
def det_aft_example_resource() -> str:
    example = {
        "request_id": "ems-dev",
        "aft": {
            "control_tower_parameters": {
                "AccountEmail": "abc@example.com",
                "AccountName": "EMS Dev",
                "ManagedOrganizationalUnit": "Dev (ou-1234567890)",
                "SSOUserEmail": "ems-team@example.com",
                "SSOUserFirstName": "Aditya",
                "SSOUserLastName": "jha",
            },
            "custom_fields": {
                "github_actions_subject_patterns": [
                    "repo:org/repo:ref:refs/heads/main"
                ],
                "enable_private_dns_rfc": True,
                "project_name": "ems",
                "terraform_cloud_project": "EMS",
                "region": "us-east-1",
                "vpc_size": "small",
            },
            "change_management_parameters": {
                "change_requested_by": "U123",
                "change_reason": "Onboarding a new workload.",
            },
        },
    }
    return json.dumps(example, indent=2)


@mcp.resource("det://policies/naming")
def det_naming_resource() -> str:
    return (
        "Project slug: lowercase project name with non-alphanumeric characters "
        "converted to hyphens.\n"
        "HCP project: uppercase project name with non-alphanumeric characters "
        "converted to hyphens.\n"
        "Workspace: HCP project for Prod; HCP project plus -Dev or -QA for "
        "non-production environments.\n"
        "Private DNS: <project-slug>-<env>.<region>.internal.det.salesforce.com "
        "for non-prod, and <project-slug>.<region>.internal.det.salesforce.com "
        "for Prod.\n"
    )


@mcp.tool()
def det_get_intake_schema() -> dict[str, Any]:
    return intake_schema()


@mcp.tool()
def det_validate_intake(candidate: dict[str, Any]) -> dict[str, Any]:
    return validate_intake(candidate)


@mcp.tool()
def det_normalize_project(candidate: dict[str, Any]) -> dict[str, Any]:
    intake = normalize_intake(candidate)
    return {
        "project_name": intake["project_name"],
        "project_slug": intake["project_slug"],
        "project_upper": intake["project_upper"],
        "github_branch": sanitize_git_branch_from_project_name(
            intake.get("project_name") or intake.get("project_slug") or "intake"
        ),
    }


@mcp.tool()
def det_preview_request(
    candidate: dict[str, Any],
    slack_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return preview_request(candidate, slack_user or {})


@mcp.tool()
def det_commit_intake_to_github(
    candidate: dict[str, Any],
    slack_user: dict[str, Any] | None = None,
    approval_token: str = "",
) -> dict[str, Any]:
    _require_write_approval(approval_token)
    validation = validate_intake(candidate)
    if not validation["valid"]:
        return {
            "status": "invalid",
            "missing_fields": validation["missing_fields"],
            "errors": validation["errors"],
        }

    intake = validation["intake"]
    default_path, payload = build_github_intake_document(intake, slack_user or {})
    path = os.environ.get("GITHUB_FILE_PATH", "").strip() or default_path
    owner = os.environ.get("GITHUB_OWNER", "adityajhacse").strip()
    repo = os.environ.get("GITHUB_REPO", "test").strip()
    base_branch = os.environ.get("GITHUB_BASE_BRANCH", "main").strip()
    project_branch = sanitize_git_branch_from_project_name(
        intake.get("project_name") or intake.get("project_slug") or "intake"
    )

    if _dry_run_enabled():
        return {
            "status": "dry_run",
            "owner": owner,
            "repo": repo,
            "branch": project_branch,
            "base_branch": base_branch,
            "path": path,
            "request_id": payload.get("request_id"),
            "message": "DET_DRY_RUN is enabled; GitHub was not modified.",
            "payload": payload,
        }

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        return {
            "status": "error",
            "message": "Missing GITHUB_TOKEN environment variable.",
        }

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
    return {
        "status": "committed",
        "owner": owner,
        "repo": repo,
        "branch": project_branch,
        "path": path,
        "request_id": payload.get("request_id"),
        "url": (result.get("content") or {}).get("html_url", ""),
    }


@mcp.tool()
def det_create_hcp_project(
    candidate: dict[str, Any],
    approval_token: str = "",
) -> dict[str, Any]:
    _require_write_approval(approval_token)
    validation = validate_intake(candidate)
    if not validation["valid"]:
        return {
            "status": "invalid",
            "missing_fields": validation["missing_fields"],
            "errors": validation["errors"],
        }

    intake = validation["intake"]
    project_name = intake["project_upper"]
    if _dry_run_enabled():
        workspace_names = intake.get("workspace_names")
        if not isinstance(workspace_names, dict):
            workspace_names = {}
        return {
            "status": "dry_run",
            "project_name": project_name,
            "workspaces": [
                workspace_names.get(env) or f"{intake['project_slug']}-{env.lower()}"
                for env in (intake.get("environments") or [])
            ],
            "message": "DET_DRY_RUN is enabled; HCP Terraform was not modified.",
        }

    workspace_names = intake.get("workspace_names")
    if not isinstance(workspace_names, dict):
        workspace_names = {}
    created = create_project_with_workspaces(
        project_name=project_name,
        project_slug=intake["project_slug"],
        environments=list(intake.get("environments") or []),
        terraform_repo=intake["terraform_repo"],
        workspace_names=workspace_names,
    )
    return {
        "status": "created",
        "project_name": created["project_name"],
        "workspaces": created.get("workspace_names", []),
    }


def _require_write_approval(approval_token: str) -> None:
    expected = os.environ.get("DET_MCP_WRITE_TOKEN", "").strip()
    if not expected or approval_token != expected:
        raise PermissionError("Write tools require Slack approval.")


def _dry_run_enabled() -> bool:
    raw = os.environ.get("DET_DRY_RUN", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
