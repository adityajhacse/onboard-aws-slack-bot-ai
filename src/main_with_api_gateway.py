# Entry point: bootstraps the Slack app and registers all command modules.
#
# Module layout:
#   aws_det_form.py   – /aws-det-poc slash command and intake/summary form handlers
#   aws_det_chat.py   – /aws-det-onboard slash command, message events, chat actions
#   aws_det_status.py – /aws-det-onboard-status slash command

import logging
import os
import ssl
from pathlib import Path

import certifi
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

import aws_det_chat
import aws_det_form
import aws_det_status
from api_gateway_client import ApiGatewayClient

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

api_client = ApiGatewayClient()

ssl_context = ssl.create_default_context(cafile=certifi.where())
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"], ssl=ssl_context)
app = App(client=client)

# Register feature modules
aws_det_form.register(app, api_client)
aws_det_chat.register(app, api_client)
aws_det_status.register(app)


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
