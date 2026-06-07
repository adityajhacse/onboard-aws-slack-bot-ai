# AWS DET Chat Implementation Summary

This document explains what was implemented for `/aws-det-onboard`, how the Python files are connected, how the function calls move through the system, and where to troubleshoot when Slack does not respond.

Note: the Slack bot entrypoint is `src/main.py`.

## What `/aws-det-onboard` Does

`/aws-det-onboard` adds an AI-assisted conversational intake flow next to the existing `/aws-det-poc` modal flow.

The user can provide DET onboarding details in natural language, for example:

```text
Create a Dev NEWEMS project in us-east-1, small VPC, service EMS API, team DL ems-team@example.com because this is for a new workload
```

The bot then:

1. Captures the Slack message.
2. Creates or continues an in-memory chat session.
3. Extracts structured DET intake fields.
4. Validates the intake through the local MCP server.
5. Asks for missing details or shows a preview.
6. Displays `Approve`, `Open Form`, and `Cancel` buttons.
7. On approval, calls MCP write tools.
8. Defaults to `DET_DRY_RUN=true`, so GitHub and HCP Terraform are not modified until dry run is disabled.

## Files Added or Updated

| File | Purpose |
| --- | --- |
| `src/main.py` | Slack command/event/action wiring for `/aws-det-onboard` |
| `src/ai_orchestrator.py` | Conversation state handling, AI extraction, MCP tool calls, approval flow |
| `src/session_store.py` | In-memory Slack session storage |
| `src/mcp_client.py` | Local MCP stdio client that starts `src/mcp_server.py` |
| `src/mcp_server.py` | Local DET MCP server exposing validation, preview, GitHub, and HCP tools |
| `src/det_intake.py` | DET schema, normalization, validation, preview text, DNS/workspace naming |
| `requirements.txt` | Adds `mcp` and `openai` dependencies |
| `.env.example` | Documents AI/MCP environment variables |

## High-Level Runtime Flow

```text
Slack user
  -> /aws-det-onboard or thread reply
  -> src/main.py
  -> DetChatOrchestrator.handle_message()
  -> LocalMcpClient.call_tool()
  -> local child process: src/mcp_server.py
  -> det_intake.py validation/preview helpers
  -> result returns to ai_orchestrator.py
  -> src/main.py posts Slack response
```

For approval:

```text
Slack Approve button
  -> src/main.py handle_det_chat_approve()
  -> DetChatOrchestrator.approve()
  -> det_validate_intake MCP tool
  -> det_commit_intake_to_github MCP tool
  -> det_create_hcp_project MCP tool
  -> Slack result message
```

## Step-by-Step: Starting `/aws-det-onboard`

### 1. Slack receives slash command

File: `src/main.py`

Function:

```python
@app.command("/aws-det-onboard")
def aws_det_chat(ack, body, client, respond):
```

What it does:

1. Reads `channel_id`, `team_id`, `user_id`, and the optional command text from Slack.
2. Calls `_channel_allowed(channel_id)` to enforce `DET_ALLOWED_CHANNELS` if configured.
3. Calls `ack()` quickly so Slack does not time out.
4. Tries to create a Slack starter message using `client.chat_postMessage(...)`.
5. If that succeeds, the starter message timestamp becomes the chat session `thread_ts`.
6. If Slack returns `channel_not_found`, it falls back to `respond(...)` using the slash-command response URL.

Important behavior:

- If the bot can post in the channel, it creates a thread and asks the user to reply there.
- If the bot cannot post in the channel, the full request can still work when sent directly inside the slash command.

## Step-by-Step: Handling the User Message

### 2. `src/main.py` calls the orchestrator

Function call:

```python
response = chat_orchestrator.handle_message(
    team_id=team_id,
    channel_id=channel_id,
    user_id=user_id,
    thread_ts=thread_ts,
    text=text,
    slack_user={"id": user_id},
)
```

The `chat_orchestrator` object is created once when `src/main.py` starts:

```python
chat_orchestrator = DetChatOrchestrator()
```

That means all active chat sessions live in memory inside the currently running Python process.

## `ai_orchestrator.py`: Conversation Brain

File: `src/ai_orchestrator.py`

Main class:

```python
class DetChatOrchestrator:
```

Important methods:

| Method | Purpose |
| --- | --- |
| `handle_message(...)` | Main entrypoint for slash commands, DMs, and thread replies |
| `approve(...)` | Handles Slack `Approve` button |
| `cancel(...)` | Handles Slack `Cancel` button |
| `has_session(...)` | Checks whether a session exists for an exact Slack key |
| `find_thread_session(...)` | Finds a session by Slack channel/thread/user |
| `_extract_updates(...)` | Extracts intake updates from natural language |

### 3. `handle_message(...)` creates or loads a session

Inside `handle_message(...)`, the first major call is:

```python
session = self.store.get_or_create(
    team_id=team_id,
    channel_id=channel_id,
    user_id=user_id,
    thread_ts=thread_ts,
)
```

This calls `src/session_store.py` and creates a session key:

```text
team_id:channel_id:thread_ts:user_id
```

The session stores:

- `candidate_intake`
- message history
- approval state
- approval token
- last preview
- timestamps

### 4. `handle_message(...)` handles reset/help/approval text

Special user messages:

| Message | Behavior |
| --- | --- |
| `reset`, `cancel`, `start over`, `restart` | Clears the in-memory session |
| empty text, `help`, `start` | Shows the intro message |
| `approve`, `submit`, `yes` | Refuses text approval and asks user to click the button |

Text approval is intentionally rejected. Approval must use the Slack button.

### 5. `handle_message(...)` extracts intake fields

Function call:

```python
updates = self._extract_updates(clean_text, session.candidate_intake)
```

`_extract_updates(...)` uses two extraction paths:

1. `_deterministic_extract(text)`
2. `_openai_extract(text, current_intake)` if `OPENAI_API_KEY` is configured

The deterministic extractor can pull common fields from text:

- environments: `Dev`, `QA`, `Prod`
- regions: `us-east-1`, `us-west-2`, `eu-west-1`
- VPC model: `Big`, `Medium`, `Small`
- team DL email
- Slack user mentions
- project name
- service name
- business justification after `because`

If OpenAI is configured, `_openai_extract(...)` sends the latest message and current intake to the configured model and asks for JSON-only field updates.

Model configuration:

```bash
OPENAI_API_KEY="sk-your-openai-api-key"
AI_PROVIDER="openai"
AI_MODEL="gpt-4o-mini"
```

If `OPENAI_API_KEY` is missing, the chatbot still works with deterministic extraction.

### 6. Extracted values are merged

Function call:

```python
session.candidate_intake = merge_intake_updates(
    session.candidate_intake,
    updates,
)
```

This function lives in `src/det_intake.py`.

It merges the latest extracted fields into the existing draft and normalizes the result.

## `det_intake.py`: DET Rules and Preview Logic

File: `src/det_intake.py`

This file owns the DET data rules used by the chatbot and MCP tools.

Important constants:

```python
ALLOWED_ENVIRONMENTS = ("Dev", "QA", "Prod")
ALLOWED_REGIONS = ("us-east-1", "us-west-2", "eu-west-1")
ALLOWED_VPC_MODELS = ("Big", "Medium", "Small")
REQUIRED_FIELDS = (...)
```

Important functions:

| Function | Purpose |
| --- | --- |
| `intake_schema()` | Returns required fields and allowed values |
| `normalize_intake(candidate)` | Cleans project name, slug, uppercase name, lists, VPC, users, and email |
| `validate_intake(candidate)` | Returns `valid`, `missing_fields`, `errors`, and normalized intake |
| `preview_request(candidate, slack_user)` | Builds request preview, DNS values, workspace names, GitHub path, AFT JSON |
| `merge_intake_updates(current, updates)` | Merges latest extracted fields into the existing draft |
| `format_missing_fields(missing_fields)` | Converts missing field names into user-friendly text |

### Normalized intake shape

The chatbot works toward this shape:

```json
{
  "project_name": "NEWEMS",
  "project_slug": "newems",
  "project_upper": "NEWEMS",
  "environments": ["Dev"],
  "regions": ["us-east-1"],
  "vpc_model": "Small",
  "service_name": "EMS API",
  "business_justification": "this is for a new workload",
  "members": [],
  "team_dl": "ems-team@example.com"
}
```

This is intentionally similar to the modal intake shape from `src/modal_lib.py`.

## `mcp_client.py`: Calling the Local MCP Server

File: `src/mcp_client.py`

Main class:

```python
class LocalMcpClient:
```

Important method:

```python
call_tool(name, arguments, extra_env=None)
```

What it does:

1. Starts `src/mcp_server.py` as a local child process using the current Python interpreter.
2. Connects to it over MCP stdio.
3. Initializes an MCP `ClientSession`.
4. Calls the requested tool.
5. Decodes the tool result into a normal Python dictionary.

Example from `ai_orchestrator.py`:

```python
validation = self.mcp.call_tool(
    "det_validate_intake",
    {"candidate": session.candidate_intake},
)
```

The MCP server is local. There is no remote MCP service in this PoC.

## `mcp_server.py`: Local DET MCP Tools

File: `src/mcp_server.py`

Server setup:

```python
mcp = FastMCP("aws-det-poc")
```

The server starts when run as a script:

```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

`mcp_client.py` starts this script as a child process whenever it calls a tool.

### MCP resources

| Resource | Purpose |
| --- | --- |
| `det://schema/intake` | JSON schema-like description of required DET fields |
| `det://examples/aft-request` | Example AFT request |
| `det://policies/naming` | Naming rules for slug, HCP project, workspaces, and DNS |

### MCP tools

| Tool | Called by | Purpose |
| --- | --- | --- |
| `det_get_intake_schema` | Future/read-only flows | Returns intake schema |
| `det_validate_intake` | `handle_message(...)`, `approve(...)` | Validates current draft |
| `det_normalize_project` | Future/read-only flows | Returns normalized project naming |
| `det_preview_request` | `handle_message(...)` | Builds final preview |
| `det_commit_intake_to_github` | `approve(...)` | Commits approved JSON to GitHub, or dry-runs |
| `det_create_hcp_project` | `approve(...)` | Creates HCP Terraform project, or dry-runs |

### Write protection

Write tools call:

```python
_require_write_approval(approval_token)
```

The expected token comes from:

```python
DET_MCP_WRITE_TOKEN
```

This token is generated only during Slack button approval. The model or user text cannot trigger write tools directly.

### Dry-run protection

By default:

```bash
DET_DRY_RUN=true
```

When dry run is enabled:

- `det_commit_intake_to_github` returns what it would commit.
- `det_create_hcp_project` returns what project it would create.
- GitHub and HCP Terraform are not modified.

Set this only when ready for real writes:

```bash
DET_DRY_RUN=false
```

## Approval Flow

### 7. Preview creates Slack buttons

When `det_preview_request` returns a valid preview, `ai_orchestrator.py` stores:

```python
session.preview = preview
session.approval_state = "pending_approval"
```

Then it returns Slack blocks from:

```python
_approval_blocks(session.key, full_text)
```

Buttons:

- `Approve`
- `Open Form`
- `Cancel`

The button value is the session key.

### 8. User clicks `Approve`

File: `src/main.py`

Function:

```python
@app.action("det_chat_approve")
def handle_det_chat_approve(ack, body, respond):
```

It calls:

```python
response = chat_orchestrator.approve(
    session_key=session_key,
    slack_user=body.get("user") or {},
)
```

### 9. `approve(...)` performs approved MCP writes

File: `src/ai_orchestrator.py`

Function:

```python
def approve(...)
```

Flow:

1. Load session from in-memory store.
2. Confirm `approval_state == "pending_approval"`.
3. Generate a temporary approval token.
4. Pass that token as `DET_MCP_WRITE_TOKEN` into the MCP child process.
5. Call `det_validate_intake`.
6. Call `det_commit_intake_to_github`.
7. If GitHub succeeds or dry-runs, call `det_create_hcp_project`.
8. Mark session as `submitted`.
9. Return final Slack text.

## Slack Event Handling

`src/main.py` listens to slash commands and message events for chatbot interactions.

### Slash command

```python
@app.command("/aws-det-onboard")
```

Starts a new session.

### Message events

```python
@app.event("message")
```

Handles:

- DMs
- normal thread replies
- `message_replied` subtype events

The handler logs incoming events:

```text
Slack message event subtype=... channel_type=... channel=... user=... thread_ts=... ts=... has_text=...
```

This log is important for troubleshooting. If you reply in Slack and do not see this log, Slack is not delivering message events to the bot.

## Session Storage

File: `src/session_store.py`

Main classes/functions:

| Name | Purpose |
| --- | --- |
| `ChatSession` | Dataclass holding session state |
| `InMemorySessionStore` | Thread-safe in-memory store |
| `build_session_key(...)` | Builds `team_id:channel_id:thread_ts:user_id` |
| `get_or_create(...)` | Creates or returns a session |
| `find_thread_session(...)` | Finds a session by channel/thread/user |
| `reset(...)` | Deletes a session |

Sessions expire after:

```python
SESSION_TTL = timedelta(minutes=60)
```

Because this is in memory, sessions are lost when the Python process restarts.

## Full Example Flow

### User action

```text
/aws-det-onboard
```

Bot response:

```text
Send the DET request details in one message, or answer step by step...
Reply in this thread with the request details or corrections.
```

### User replies in thread

```text
Create a Dev NEWEMS project in us-east-1, small VPC, service EMS API, team DL ems-team@example.com because this is for a new workload
```

Call path:

```text
src/main.py handle_chat_message()
  -> chat_orchestrator.find_thread_session()
  -> chat_orchestrator.handle_message()
  -> _extract_updates()
  -> merge_intake_updates()
  -> mcp.call_tool("det_validate_intake")
  -> src/mcp_client.py starts src/mcp_server.py
  -> src/mcp_server.py det_validate_intake()
  -> src/det_intake.py validate_intake()
  -> mcp.call_tool("det_preview_request")
  -> src/det_intake.py preview_request()
  -> Slack preview with buttons
```

### User clicks `Approve`

Call path:

```text
src/main.py handle_det_chat_approve()
  -> chat_orchestrator.approve()
  -> mcp.call_tool("det_validate_intake")
  -> mcp.call_tool("det_commit_intake_to_github")
  -> mcp.call_tool("det_create_hcp_project")
  -> Slack final result
```

With `DET_DRY_RUN=true`, final result is a dry run and no external systems are changed.

## Required Environment Variables

Core Slack variables:

```bash
SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
SLACK_APP_TOKEN="xapp-your-slack-app-token"
```

AI variables:

```bash
OPENAI_API_KEY="sk-your-openai-api-key"
AI_PROVIDER="openai"
AI_MODEL="gpt-4o-mini"
```

Safety:

```bash
DET_DRY_RUN="true"
```

Optional channel allowlist:

```bash
DET_ALLOWED_CHANNELS="C0123456789,C9876543210"
```

GitHub and HCP variables are required only when dry run is disabled and real writes are expected:

```bash
GITHUB_TOKEN="ghp-your-token"
GITHUB_OWNER="your-org"
GITHUB_REPO="your-repo"
GITHUB_BASE_BRANCH="main"
HCP_TERRAFORM_TOKEN="your-token"
HCP_TERRAFORM_ORG="your-org"
```

## Slack App Configuration Checklist

For `/aws-det-onboard`:

1. Add slash command `/aws-det-onboard`.
2. Enable Interactivity.
3. Add bot scope `commands`.
4. Add bot scope `chat:write`.

For channel threads:

1. Invite the bot to the channel:

   ```text
   /invite @aws-det-bot-poc
   ```

2. Enable Event Subscriptions.
3. Add bot event `message.channels`.
4. Add bot scope `channels:history`.
5. Reinstall the Slack app after changing scopes or events.

For DMs:

1. Add relevant DM message event based on workspace policy.
2. Add the matching DM history scope.

## Troubleshooting

### `/aws-det-onboard` opens the intro but thread replies do nothing

Check terminal logs.

Expected log after replying:

```text
Slack message event subtype=... channel_type=... channel=... user=... thread_ts=... ts=... has_text=True
```

If that log is missing:

- Slack Event Subscriptions may not be enabled.
- `message.channels` may not be configured.
- `channels:history` scope may be missing.
- Slack app may need reinstall after scope/event changes.
- Bot may not be invited to the channel.

If the log exists but no preview appears:

- Look for `Continuing DET chatbot thread session...`.
- If missing, the message did not match an active in-memory session.
- Start a fresh `/aws-det-onboard` after restarting the bot.
- Remember sessions are lost on process restart.

### `channel_not_found`

This means the bot token cannot post to that channel.

Fix:

```text
/invite @aws-det-bot-poc
```

Fallback:

```text
/aws-det-onboard Create a Dev NEWEMS project in us-east-1, small VPC, service EMS API, team DL ems-team@example.com because this is for a new workload
```

### Approval says dry run

That is expected when:

```bash
DET_DRY_RUN=true
```

Set `DET_DRY_RUN=false` only when GitHub and HCP Terraform writes should happen for real.

### MCP dependency missing

Install dependencies:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### OpenAI is not being called

Check:

```bash
OPENAI_API_KEY
AI_PROVIDER
AI_MODEL
```

If `OPENAI_API_KEY` is missing, the deterministic extractor still runs, but the model-based extraction is skipped.

### GitHub write fails

Check:

- `DET_DRY_RUN=false`
- `GITHUB_TOKEN`
- `GITHUB_OWNER`
- `GITHUB_REPO`
- `GITHUB_BASE_BRANCH`
- repository permissions

The MCP tool involved is:

```python
det_commit_intake_to_github(...)
```

### HCP Terraform create fails

Check:

- `DET_DRY_RUN=false`
- `HCP_TERRAFORM_TOKEN`
- `HCP_TERRAFORM_ORG`
- `HCP_TERRAFORM_URL`

The MCP tool involved is:

```python
det_create_hcp_project(...)
```

## Quick Local Verification Commands

Run from the repository root.

Validate Python syntax:

```bash
.venv/bin/python -m py_compile src/main.py src/ai_orchestrator.py src/mcp_client.py src/mcp_server.py src/det_intake.py src/session_store.py
```

Test MCP validation:

```bash
PYTHONPATH=src .venv/bin/python -c "from mcp_client import LocalMcpClient; c=LocalMcpClient(); print(c.call_tool('det_validate_intake', {'candidate': {'project_name':'NEWEMS','environments':['Dev'],'regions':['us-east-1'],'vpc_model':'Small','service_name':'EMS API','business_justification':'new workload','team_dl':'ems-team@example.com'}}))"
```

Test orchestrator preview:

```bash
PYTHONPATH=src .venv/bin/python -c "from ai_orchestrator import DetChatOrchestrator; o=DetChatOrchestrator(); r=o.handle_message(team_id='T1', channel_id='C1', user_id='U1', thread_ts='default', text='Create a Dev NEWEMS project in us-east-1, small VPC, service EMS API, team DL ems-team@example.com because this is for a new workload', slack_user={'id':'U1'}); print(r.text); print(bool(r.blocks))"
```

## Summary

`/aws-det-onboard` is a local PoC conversational layer around the existing DET bot. Slack events enter through `src/main.py`, conversation state and AI extraction live in `src/ai_orchestrator.py`, sessions are stored in memory by `src/session_store.py`, MCP calls are made through `src/mcp_client.py`, MCP tools are exposed by `src/mcp_server.py`, and DET-specific validation/preview rules live in `src/det_intake.py`.

The safest way to think about the design is:

```text
Slack handles interaction.
ai_orchestrator.py handles conversation.
mcp_client.py and mcp_server.py handle tool boundaries.
det_intake.py handles DET business rules.
GitHub and HCP writes happen only after Slack button approval.
```
