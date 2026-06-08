# Installation Guide

## Install Python Dependencies

### Option 1: Using requirements.txt (Recommended)

```bash
cd src
pip3 install -r requirements.txt
```

Or if you have pip issues:
```bash
python3 -m pip install -r requirements.txt
```

### Option 2: Install Individually

```bash
pip3 install slack-sdk
pip3 install slack-bolt
pip3 install requests
pip3 install certifi
```

### Option 3: Using Virtual Environment (Best Practice)

```bash
cd src

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Mac/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Verify Installation

```bash
cd src
python3 -c "import requests; import slack_sdk; import slack_bolt; print('All dependencies installed!')"
```

Expected output:
```
All dependencies installed!
```

---

## Set Environment Variables

Create a `.env` file in the `src` directory:

```bash
cd src
cat > .env << 'EOF'
# Slack Tokens
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# Status API URL (from API Gateway)
STATUS_API_URL=https://xxxxx.execute-api.us-east-1.amazonaws.com/prod

# Optional: DET Allowed Channels
DET_ALLOWED_CHANNELS=["C123456789"]
EOF
```

---

## Run the Bot

```bash
cd src
python3 main_with_api_gateway.py
```

You should see:
```
INFO:slack_bolt.App:Starting to receive messages from a new connection
```

---

## Common Issues

### Issue: "No module named 'requests'"

**Solution:**
```bash
pip3 install requests
# OR
python3 -m pip install requests
```

### Issue: "No module named 'slack_sdk'"

**Solution:**
```bash
pip3 install slack-sdk slack-bolt
```

### Issue: Proxy/Network errors during pip install

**Solution 1 - Bypass proxy:**
```bash
pip3 install --proxy="" requests slack-sdk slack-bolt
```

**Solution 2 - Use different index:**
```bash
pip3 install -i https://pypi.python.org/simple/ requests
```

**Solution 3 - Download and install offline:**
1. Go to https://pypi.org/project/requests/#files
2. Download the wheel file (.whl)
3. Install: `pip3 install requests-2.31.0-py3-none-any.whl`

### Issue: Permission denied

**Solution:**
```bash
pip3 install --user requests slack-sdk slack-bolt
```

---

## For Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/det-bot.service`:

```ini
[Unit]
Description=AWS DET Onboarding Slack Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/src
Environment="SLACK_BOT_TOKEN=xoxb-..."
Environment="SLACK_APP_TOKEN=xapp-..."
Environment="STATUS_API_URL=https://..."
ExecStart=/usr/bin/python3 main_with_api_gateway.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl enable det-bot
sudo systemctl start det-bot
sudo systemctl status det-bot
```

### Using Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main_with_api_gateway.py"]
```

Build and run:
```bash
docker build -t det-bot .
docker run -d \
  --name det-bot \
  -e SLACK_BOT_TOKEN=xoxb-... \
  -e SLACK_APP_TOKEN=xapp-... \
  -e STATUS_API_URL=https://... \
  --restart unless-stopped \
  det-bot
```

### Using AWS Lambda (Alternative)

If you want to run the bot on Lambda instead of a server:

1. Package the bot with dependencies
2. Deploy as Lambda function
3. Use Lambda URLs or API Gateway
4. Configure Slack to POST to Lambda URL

Note: This requires additional configuration for WebSocket connections.

---

## Health Check

Test that everything works:

```bash
# Test 1: Import check
python3 -c "from status_api_client import StatusApiClient; print('OK')"

# Test 2: API connectivity
python3 -c "
import os
os.environ['STATUS_API_URL'] = 'https://your-api-url'
from status_api_client import StatusApiClient
client = StatusApiClient()
print('API client initialized')
"

# Test 3: Slack connectivity
python3 -c "
import os
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-your-token'
from slack_sdk import WebClient
client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
response = client.auth_test()
print(f'Bot connected: {response[\"user\"]}')
"
```

---

## Ready!

Once all dependencies are installed and environment variables are set, you can run:

```bash
cd src
python3 main_with_api_gateway.py
```

The bot should start and be ready to receive commands! 🚀
