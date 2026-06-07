import json
import re


def welcome_page(body, client, channel_id):
    """DET Onboarding Intake — modal opened from /aws-det-poc."""
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "det_intake_modal",
            "private_metadata": json.dumps(
                {
                    "channel_id": channel_id or "",
                    "user_id": body.get("user_id", ""),
                }
            ),
            "title": {"type": "plain_text", "text": "DET Onboarding Intake"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": _det_intake_blocks(),
        },
    )


def build_submission_summary_view(view):
    intake = _extract_submission(view)
    metadata = _build_summary_metadata(view.get("private_metadata", ""), intake)

    return {
        "type": "modal",
        "callback_id": "det_summary_modal",
        "private_metadata": metadata,
        "title": {"type": "plain_text", "text": "DET Details"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": _det_summary_blocks(intake),
    }


def build_processed_confirmation_view(success, project_name, detail):
    if success:
        title = "Request Processed"
        body = (
            ":white_check_mark: *Your request has been processed.*\n\n"
            f"HCP Terraform project `{project_name}` has been created.\n"
            f"{detail}\n"
            "We will inform you once we deploy things for you. Please contact the DET Platform team if you have any questions."
        )
    else:
        title = "Request Failed"
        body = (
            ":warning: *We could not process your request completely.*\n\n"
            f"HCP Terraform project `{project_name}` was not created.\n"
            f"*Details:* {detail}"
        )

    return {
        "type": "modal",
        "callback_id": "det_processed_modal",
        "clear_on_close": True,
        "title": {"type": "plain_text", "text": title},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": body,
                },
            }
        ],
    }


def build_processing_view(project_name):
    return {
        "type": "modal",
        "callback_id": "det_processing_modal",
        "title": {"type": "plain_text", "text": "Processing"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f":hourglass_flowing_sand: Creating HCP Terraform project `{project_name}`.\n\n"
                        "Please wait while we process your request."
                    ),
                },
            }
        ],
    }


def _det_intake_blocks():
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*DET Onboarding Intake Workflow* — end-to-end request form.",
            },
        },
        {"type": "divider"},
        # 1. Project/Workload Name
        {
            "type": "input",
            "block_id": "project_name_block",
            "optional": False,
            "label": {"type": "plain_text", "text": "1. Project/Workload Name"},
            "element": {
                "type": "plain_text_input",
                "action_id": "project_name",
                "placeholder": {
                    "type": "plain_text",
                    "text": "e.g. EMS",
                },
            },
        },
        # 2. Environment (checkboxes)
        {
            "type": "input",
            "block_id": "environment_block",
            "optional": False,
            "label": {
                "type": "plain_text",
                "text": "2. Environment — select all that apply",
            },
            "element": {
                "type": "checkboxes",
                "action_id": "environment",
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "Dev"},
                        "value": "Dev",
                    },
                    {
                        "text": {"type": "plain_text", "text": "QA"},
                        "value": "QA",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Prod"},
                        "value": "Prod",
                    },
                ],
            },
        },
        # 2b. Terraform GitHub repository
        {
            "type": "input",
            "block_id": "terraform_repo_block",
            "optional": False,
            "label": {"type": "plain_text", "text": "Terraform GitHub repo (owner/repo)"},
            "element": {
                "type": "external_select",
                "action_id": "terraform_repo",
                "min_query_length": 0,
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an existing GitHub repository",
                },
            },
        },
        # 3. Region (checkboxes)
        {
            "type": "input",
            "block_id": "region_block",
            "optional": False,
            "label": {
                "type": "plain_text",
                "text": "3. Region — select all that apply",
            },
            "element": {
                "type": "checkboxes",
                "action_id": "region",
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "us-east-1"},
                        "value": "us-east-1",
                    },
                    {
                        "text": {"type": "plain_text", "text": "us-west-2"},
                        "value": "us-west-2",
                    },
                    {
                        "text": {"type": "plain_text", "text": "eu-west-1"},
                        "value": "eu-west-1",
                    },
                ],
            },
        },
        # 4. VPC Model (radio)
        {
            "type": "input",
            "block_id": "vpc_model_block",
            "optional": False,
            "label": {"type": "plain_text", "text": "4. VPC Model — choose one"},
            "element": {
                "type": "radio_buttons",
                "action_id": "vpc_model",
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "Big"},
                        "value": "Big",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Medium"},
                        "value": "Medium",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Small"},
                        "value": "Small",
                    },
                ],
            },
        },
        # 5. Service Name
        {
            "type": "input",
            "block_id": "service_name_block",
            "optional": False,
            "label": {"type": "plain_text", "text": "5. Service Name"},
            "element": {
                "type": "plain_text_input",
                "action_id": "service_name",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Service being onboarded",
                },
            },
        },
        # 6. Business Justification
        {
            "type": "input",
            "block_id": "business_justification_block",
            "optional": False,
            "label": {"type": "plain_text", "text": "6. Business Justification"},
            "element": {
                "type": "plain_text_input",
                "action_id": "business_justification",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "Brief description of the business need",
                },
            },
        },
        # 7. Members (HCP project)
        {
            "type": "input",
            "block_id": "members_block",
            "optional": True,
            "label": {
                "type": "plain_text",
                "text": "7. Add members to manage HCP Project",
            },
            "element": {
                "type": "multi_users_select",
                "action_id": "members",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select Slack sandbox users",
                },
            },
        },
        # 8. Team DL
        {
            "type": "input",
            "block_id": "team_dl_block",
            "optional": False,
            "label": {"type": "plain_text", "text": "8. Team Distribution List (DL)"},
            "element": {
                "type": "plain_text_input",
                "action_id": "team_dl",
                "placeholder": {
                    "type": "plain_text",
                    "text": "e.g. team-ems@salesforce.com",
                },
            },
        },
        # 9. Team Channel
        {
            "type": "input",
            "block_id": "team_channel_block",
            "optional": False,
            "label": {"type": "plain_text", "text": "9. Team Channel"},
            "element": {
                "type": "conversations_select",
                "action_id": "team_channel",
                "default_to_current_conversation": False,
                "filter": {
                    "include": ["public", "private"],
                    "exclude_external_shared_channels": True,
                    "exclude_bot_users": True,
                },
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an existing Slack channel",
                },
            },
        },
    ]


def extract_intake_submission(view):
    """Public entry for Slack ``view`` payloads (used by ``main`` after intake Submit)."""
    return _extract_submission(view)


def _extract_submission(view):
    state_values = view["state"]["values"]

    project_name = _get_input_value(
        state_values, "project_name_block", "project_name"
    ).strip()
    environments = _get_selected_values(
        state_values, "environment_block", "environment"
    )
    terraform_repo = _get_selected_value(
        state_values, "terraform_repo_block", "terraform_repo"
    ).strip()
    regions = _get_selected_values(state_values, "region_block", "region")
    vpc_model = _get_selected_value(state_values, "vpc_model_block", "vpc_model")
    service_name = _get_input_value(state_values, "service_name_block", "service_name")
    business_justification = _get_input_value(
        state_values, "business_justification_block", "business_justification"
    )
    members = _get_selected_users(state_values, "members_block", "members")
    team_dl = _get_input_value(state_values, "team_dl_block", "team_dl")
    team_channel = _get_selected_conversation(
        state_values, "team_channel_block", "team_channel"
    )

    return {
        "project_name": project_name,
        "project_slug": _slugify_project_name(project_name),
        "project_upper": _project_upper(project_name),
        "terraform_repo": terraform_repo,
        "workspace_mode": "default",
        "workspace_names": {},
        "environments": environments,
        "regions": regions,
        "vpc_model": vpc_model,
        "service_name": service_name,
        "business_justification": business_justification,
        "members": members,
        "team_dl": team_dl,
        "team_channel": team_channel,
    }


def _det_summary_blocks(intake):
    summary_text = "\n".join(
        [
            f"*Project Name:* {intake['project_name']}",
            f"*Service Name:* {intake['service_name']}",
            f"*VPC Model:* {intake['vpc_model']}",
            f"*Environment(s):* {_format_list(intake['environments'])}",
            f"*Terraform repo:* {intake.get('terraform_repo', '-')}",
            f"*Region(s):* {_format_list(intake['regions'])}",
            f"*Team DL:* {intake['team_dl']}",
            f"*Team Channel:* {_format_channel(intake.get('team_channel', ''))}",
        ]
    )

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "DET Generated Configuration"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "This details are generated from the submitted project details. "
                    "Please review the information and confirm the request. If you have any questions, please contact the DET Platform team."
                ),
            },
        },
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": summary_text}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Business Justification:*\n{intake['business_justification']}",
            },
        },
    ]

    if intake["members"]:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*HCP Members:*\n"
                    + "\n".join(f"• <@{member}>" for member in intake["members"]),
                },
            }
        )

    blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Private DNS values*",
                },
            },
        ]
    )
    blocks.extend(_private_dns_blocks(intake))

    blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*HCP Project and Workspace names*",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*HCP Terraform Project:* `{intake['project_upper']}`\n"
                        + _workspace_lines(intake)
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Selected key/value model*\n"
                        f"• `project_name`: `{intake['project_name']}`\n"
                        f"• `project_slug`: `{intake['project_slug']}`\n"
                        f"• `hcp_project`: `{intake['project_upper']}`\n"
                        f"• `regions`: `{', '.join(intake['regions'])}`\n"
                        f"• `environments`: `{', '.join(intake['environments'])}`\n"
                        f"• `terraform_repo`: `{intake.get('terraform_repo', '')}`\n"
                        f"• `team_dl`: `{intake['team_dl']}`\n"
                        f"• `team_channel`: `{intake.get('team_channel', '')}`"
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": _sso_identity_text(intake["project_upper"]),
                },
            },
        ]
    )

    return blocks


def _private_dns_blocks(intake):
    dns_lines = []
    for environment in intake["environments"]:
        for region in intake["regions"]:
            dns_lines.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{environment} / {region}*\n"
                            f"`{_private_dns_value(intake['project_slug'], environment, region)}`"
                        ),
                    },
                }
            )
    return dns_lines


def _workspace_lines(intake):
    return "\n".join(
        f"• *{environment}:* `{_workspace_name(intake['project_slug'], environment)}`"
        for environment in intake["environments"]
    )


def _private_dns_value(project_slug, environment, region):
    env = environment.upper()
    if env == "Prod":
        prefix = project_slug
    else:
        prefix = f"{project_slug}-{env.lower()}"
    return f"{prefix}.{region}.internal.det.salesforce.com"


def _workspace_name(project_slug, environment):
    return f"{project_slug}-wspace-{environment.lower()}"


def _get_input_value(state_values, block_id, action_id):
    return state_values[block_id][action_id].get("value", "")


def _get_selected_values(state_values, block_id, action_id):
    selected = state_values[block_id][action_id].get("selected_options", [])
    return [option["value"] for option in selected]


def _get_selected_value(state_values, block_id, action_id):
    selected = state_values[block_id][action_id].get("selected_option")
    return selected["value"] if selected else ""


def _get_selected_users(state_values, block_id, action_id):
    return state_values[block_id][action_id].get("selected_users", [])


def _get_selected_conversation(state_values, block_id, action_id):
    return state_values[block_id][action_id].get("selected_conversation", "")


def _slugify_project_name(project_name):
    normalized = re.sub(r"[^a-z0-9]+", "-", project_name.strip().lower())
    return normalized.strip("-")


def _project_upper(project_name):
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", project_name.strip()).strip("-")
    return cleaned.upper()


def _format_list(values):
    return ", ".join(values) if values else "-"


def _format_channel(channel_id):
    channel = str(channel_id or "").strip()
    if not channel:
        return "-"
    return f"<#{channel}>"


def _sso_identity_text(project_name):
    return (
        "*SSO identity and entitlements*\n"
        "AWS console access naming pattern:\n"
        f"`AWS_{project_name}_<Env>_<AWSAccountID>_<Tier>`\n\n"
        "• Read Only\n"
        "• Developer\n"
        "• Data Science\n"
        "• Power User\n"
        "• Admin\n\n"
        f"_Example:_ `AWS_{project_name}_Dev_123456789012_ReadOnly`"
    )


def _build_summary_metadata(raw_metadata, intake):
    metadata = {}
    if raw_metadata:
        try:
            metadata = json.loads(raw_metadata)
        except json.JSONDecodeError:
            metadata = {}

    metadata["intake"] = {
        "project_name": intake["project_name"],
        "project_upper": intake["project_upper"],
        "project_slug": intake["project_slug"],
    }
    return json.dumps(metadata)
