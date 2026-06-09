
# Build and push multi-arch image from Mac Silicon:
# docker buildx build --platform linux/amd64,linux/arm64 \
# -t 916657620953.dkr.ecr.us-west-2.amazonaws.com/ep-foundry-repo:latest \
# --push .

# ECS deployment: see ecs-task-definition.json and setup-secrets.sh
# All secrets (tokens, API keys) are injected at runtime by ECS from AWS Secrets Manager.
# Non-sensitive config is set in the environment[] block of the task definition.
# Do NOT hardcode secrets here or in any ENV instruction.


FROM python:3.12-slim

# Labels as key value pair
# LABEL Maintainer="roushan.me17"

WORKDIR /usr/app/src

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ai_orchestrator.py ./
COPY api_gateway_client.py ./
COPY aws_det_chat.py ./
COPY aws_det_form.py ./
COPY aws_det_status.py ./
COPY det_intake.py ./
COPY github_api.py ./
COPY hcp_terraform.py ./
COPY main_with_api_gateway.py ./
COPY mcp_client.py ./
COPY mcp_server.py ./
COPY modal_lib.py ./
COPY session_store.py ./
COPY status_api_client.py ./

CMD [ "python", "./main_with_api_gateway.py"]