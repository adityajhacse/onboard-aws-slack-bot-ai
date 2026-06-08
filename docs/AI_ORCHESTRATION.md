# AI Orchestration - Chat-Based Onboarding

Learn how to use the AI-powered chat interface for natural language infrastructure onboarding.

---

## Overview

The AI Orchestration feature allows users to request infrastructure through natural conversation instead of filling forms. The AI extracts requirements from your messages and builds the onboarding request interactively.

---

## Two Interaction Modes

### 1. Form-Based (Traditional)
```
Command: /aws-det-poc
```
- Opens a structured Slack form
- All fields visible upfront
- Submit when complete

### 2. Chat-Based (AI-Powered)
```
Command: /aws-det-onboard [optional initial request]
```
- Natural language conversation
- AI asks follow-up questions
- Conversational requirement gathering

---

## How to Use Chat Interface

### Starting a Conversation

**Option A: Start with full request**
```
/aws-det-onboard Create a Dev environment for EMS API in us-east-1 with small VPC
```

**Option B: Start minimal**
```
/aws-det-onboard I need a new project
```

**Option C: Just the command**
```
/aws-det-onboard
```

### Example Conversation

**User:**
```
/aws-det-onboard Create a project for our new API service
```

**Bot:**
```
I'll help you set up a new project. Let me gather the details:

What's the project name?
```

**User:**
```
CustomerAPI
```

**Bot:**
```
Great! For CustomerAPI, which environments do you need?
- Dev
- QA  
- Prod

You can say "Dev and QA" or "all three"
```

**User:**
```
Dev and Prod
```

**Bot:**
```
Got it - Dev and Prod environments.

Which AWS region(s)?
- us-east-1
- us-west-2
- eu-west-1
```

**User:**
```
us-east-1
```

**Bot:**
```
What VPC size do you need?
- Small (basic workloads)
- Medium (moderate traffic)
- Big (high traffic, multiple services)
```

**User:**
```
Small VPC
```

**Bot:**
```
What's the service name being onboarded?
```

**User:**
```
Customer Management API
```

**Bot:**
```
Which GitHub repository for Terraform code?
(Type to search your repos)
```

**User:**
```
myorg/customer-api-infra
```

**Bot:**
```
What's your team's distribution list email?
```

**User:**
```
team-customer-api@company.com
```

**Bot:**
```
Which Slack channel should receive notifications?
```

**User:**
```
#team-customer-api
```

**Bot:**
```
Why is this infrastructure needed?
(Business justification)
```

**User:**
```
New customer management microservice to replace legacy monolith. Required for Q3 migration project.
```

**Bot:**
```
Perfect! Here's your onboarding request:

📋 Project Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project Name: CustomerAPI
Service: Customer Management API
Environments: Dev, Prod
Region: us-east-1
VPC Model: Small
Terraform Repo: myorg/customer-api-infra
Team DL: team-customer-api@company.com
Team Channel: #team-customer-api

Business Justification:
New customer management microservice to replace legacy monolith. 
Required for Q3 migration project.

━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Approve] [Edit] [Cancel]
```

**User clicks [Approve]**

**Bot:**
```
✅ Onboarding workflow started!

Execution ID: abc123-def456-789012

The workflow is processing in the background and will:
1. ✓ Create GitHub branch
2. ✓ Commit intake document
3. ✓ Create HCP Terraform project
4. ✓ Create Dev workspace
5. ✓ Create Prod workspace
6. ✓ Configure workspace variables

You'll receive a notification when complete (~30-45 seconds).
```

---

## Natural Language Understanding

The AI understands various ways to express requirements:

### Project Environments

All these mean the same:
- "Dev and Prod"
- "Development and Production environments"
- "dev, prod"
- "I need dev and production"
- "Both Dev and Prod please"

### VPC Sizes

Variations understood:
- "Small VPC" → Small
- "I need a small one" → Small
- "medium size" → Medium
- "big vpc for high traffic" → Big

### Regions

Flexible input:
- "us-east-1" → us-east-1
- "Virginia region" → us-east-1
- "US East" → us-east-1
- "Oregon" → us-west-2

---

## Chat Commands During Conversation

### Modify Your Request

**Start over:**
```
restart
```

**Change specific field:**
```
Actually, use us-west-2 instead
```

**Add environments:**
```
Also add QA environment
```

### Get Help

**See what's missing:**
```
what do you still need?
```

**Show current state:**
```
show me what we have so far
```

**Help with options:**
```
what vpc sizes are available?
```

---

## Approval Flow

Before execution, you'll see a summary with three options:

### [Approve] Button
- Starts the workflow immediately
- Creates GitHub branch and HCP resources
- Sends execution ID for tracking

### [Edit] Button
- Returns to conversation
- Allows modifications
- Re-presents summary after changes

### [Cancel] Button
- Abandons the request
- Clears the session
- No resources created

---

## Advanced Features

### Multi-Turn Context

The AI remembers your conversation:

```
User: Create a Dev project for API Gateway
Bot: What's the project name?
User: Actually, make it Dev and QA
Bot: Got it - I'll use Dev and QA environments. What's the project name?
```

### Correction Handling

Correct mistakes naturally:

```
User: team email is team-api@company.com
Bot: Got it.
User: wait, it should be team-apigateway@company.com
Bot: Updated to team-apigateway@company.com
```

### Abbreviation Recognition

Short forms work:

```
User: envs: dev, qa
Bot: Environments set to Dev and QA

User: vpc: small
Bot: VPC model set to Small

User: region: use1
Bot: Region set to us-east-1
```

---

## How AI Extracts Requirements

The AI orchestrator (`ai_orchestrator.py`) uses pattern matching and NLP techniques:

### 1. Intent Recognition
Identifies what you're trying to do:
- Create new project
- Modify existing request
- Ask for help
- Provide information

### 2. Entity Extraction
Pulls out specific values:
- Project names: "EMS", "CustomerAPI"
- Environments: "Dev", "Production", "QA"
- Regions: "us-east-1", "Virginia"
- VPC sizes: "small", "medium", "big"

### 3. Validation
Checks requirements:
- All required fields present
- Values are valid (regions exist, VPC size is valid)
- Email format correct
- GitHub repo accessible

### 4. Confirmation
Shows summary for approval before execution

---

## Comparison: Form vs Chat

| Aspect | Form (/aws-det-poc) | Chat (/aws-det-onboard) |
|--------|---------------------|-------------------------|
| **Speed** | Faster (if you know all values) | Slower (conversational) |
| **Flexibility** | Fixed fields | Natural language |
| **Guidance** | See all fields upfront | Guided step-by-step |
| **Corrections** | Go back and edit | Just say "actually..." |
| **Learning Curve** | Must know field names | Conversational |
| **Best For** | Repeat users, bulk requests | New users, exploratory |

---

## Tips for Best Results

### Be Specific
✅ "Create Dev and QA in us-east-1 with small VPC"  
❌ "Set up some stuff"

### Provide Context in One Message When Possible
✅ "Create a Dev EMS project in us-east-1, small VPC, service is EMS API"  
✅ (Bot needs less follow-up)

### Use Clear Project Names
✅ "CustomerAPI"  
❌ "the new thing" or "project-123-test-v2-final"

### Complete Thoughts
✅ "Team DL is team-api@company.com"  
❌ "team-api" (AI may need clarification)

---

## Session Management

### Session Persistence
- Each chat creates a session
- Session stored in memory (in-memory session store)
- Cleared after approval/cancellation

### Multi-User Support
- Each user has their own session
- Sessions identified by: team_id + channel_id + user_id + thread_ts
- No cross-contamination between users

### Thread-Based Conversations
- Continue conversation by replying in thread
- Bot maintains context within thread
- Start new request = new thread

---

## Behind the Scenes

When you chat with the bot:

1. **Message received** → `handle_message()` in `ai_orchestrator.py`
2. **Session lookup** → Finds or creates your session
3. **AI processing** → Extracts entities and intent
4. **Missing fields check** → Identifies what's still needed
5. **Response generation** → Asks follow-up questions or shows summary
6. **Validation** → Checks if ready for approval
7. **Approval** → Triggers API Gateway → Step Functions workflow

---

## Limitations

### Current Limitations

1. **No voice input** - Text only (Slack limitation)
2. **English only** - NLP optimized for English
3. **Session timeout** - 30 minutes of inactivity
4. **No history search** - Can't reference previous projects
5. **Single project per session** - One request at a time

### Planned Improvements

- Multi-project requests in one conversation
- Reference previous configurations ("same as last time")
- Template library ("use the standard API template")
- Autocomplete suggestions in Slack

---

## Troubleshooting

### Bot doesn't respond

**Check:**
- Bot is running (`python main_with_api_gateway.py`)
- You're in an allowed channel
- Thread is part of an active session

### AI doesn't understand

**Try:**
- Be more explicit: "environments: Dev and QA"
- Use standard names: "us-east-1" not "Virginia"
- Provide full context in one message

### Session lost

**Cause:** Bot restarted (in-memory sessions cleared)

**Solution:** Start new conversation with `/aws-det-onboard`

### Can't approve

**Check:**
- All required fields provided
- Values are valid
- Summary shows [Approve] button

---

## Examples: Common Requests

### Minimal Dev Environment
```
/aws-det-onboard Create Dev project TestAPI in us-east-1, small VPC, 
repo myorg/test-infra, team test@company.com, channel #test-team, 
service TestAPI, justification: testing new service
```

### Multi-Environment Production Setup
```
/aws-det-onboard Create Dev, QA, and Prod environments for CustomerAPI 
in us-east-1 and us-west-2, medium VPC, service Customer Management API, 
repo myorg/customer-infra, team customer-team@company.com, 
channel #team-customer, justification: Q3 migration from legacy system
```

### Quick Prototype
```
/aws-det-onboard
> I need a quick Dev environment
> Project: Prototype
> Repo: myorg/prototype
> Small VPC, us-east-1
> Team: prototype@company.com
> Channel: #prototypes
> Service: Prototype API
> Justification: Testing new features
```

---

## Security Notes

### Data Handling
- Messages logged for debugging (sanitized)
- Tokens never logged
- Session data in memory only
- No persistent storage of conversation history

### Approval Required
- AI never auto-submits
- Always shows summary for human approval
- User has final control

---

## Advanced: Customize AI Behavior

Edit `src/ai_orchestrator.py` to customize:

### Change prompts
```python
def _ask_for_project_name(self) -> str:
    return "What should we name this project?"
```

### Add custom patterns
```python
if "urgent" in text.lower():
    # Prioritize this request
    session.priority = "high"
```

### Modify validation
```python
def _validate_intake(self, intake: dict) -> dict:
    # Add custom validation logic
    if intake["project_name"].startswith("test-"):
        return {"valid": False, "reason": "Production names can't start with 'test-'"}
```

---

## Summary

The AI chat interface makes infrastructure onboarding conversational and intuitive:

✅ Natural language input  
✅ Guided step-by-step  
✅ Flexible corrections  
✅ Human approval required  
✅ Full context maintained  
✅ Session-based conversations

Try both `/aws-det-poc` (form) and `/aws-det-onboard` (chat) to see which you prefer!

---

**Happy chatting! 💬**
