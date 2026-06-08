# User Journey - Complete Onboarding Workflow

A step-by-step walkthrough of the complete onboarding process from user submission to infrastructure delivery.

---

## Overview

This document describes the complete journey from when a user opens Slack to when they receive fully configured infrastructure.

**Total Time:** ~2-3 minutes (form) + 30-45 seconds (automation)

---

## Journey Map

```
User Opens Slack
       ↓
   Slash Command
   (/aws-det-poc or /aws-det-onboard)
       ↓
   Fill Form / Chat
       ↓
   Submit / Approve
       ↓
   API Gateway Receives Request
       ↓
   Step Functions Starts
       ↓
   8 Lambda Functions Execute
       ↓
   Infrastructure Created
       ↓
   User Receives Notification
       ↓
   Ready to Deploy
```

---

## Step-by-Step Journey

### Step 1: User Opens Slack (T+0 sec)

**User Action:**
```
Opens Slack → Goes to allowed channel → Types command
```

**Two Options:**

#### Option A: Form-Based
```
/aws-det-poc
```
Opens structured form modal

#### Option B: Chat-Based
```
/aws-det-onboard Create a Dev project for EMS API
```
Starts AI-powered conversation

---

### Step 2: Provide Project Details (T+0 to T+2 min)

#### Form View (Option A)

User sees and fills:

```
┌─────────────────────────────────────────────┐
│  DET Onboarding Intake                      │
├─────────────────────────────────────────────┤
│                                             │
│  Project Name: [________________]           │
│                                             │
│  Terraform Repo: [▼ Select repository]     │
│                                             │
│  Team Channel: [▼ Select channel]          │
│                                             │
│  Environments:                              │
│    ☐ Dev    ☐ QA    ☐ Prod                │
│                                             │
│  Regions:                                   │
│    ☐ us-east-1                             │
│    ☐ us-west-2                             │
│    ☐ eu-west-1                             │
│                                             │
│  VPC Model:                                 │
│    ○ Small  ○ Medium  ○ Big                │
│                                             │
│  Service Name: [________________]           │
│                                             │
│  Business Justification:                    │
│  [________________________________]         │
│  [________________________________]         │
│                                             │
│  Team DL: [________________@company.com]    │
│                                             │
│         [Cancel]         [Submit]           │
└─────────────────────────────────────────────┘
```

#### Chat View (Option B)

Conversational flow:

```
Bot: What's the project name?
User: EMS

Bot: Which environments? (Dev, QA, Prod)
User: Dev and Prod

Bot: Which regions?
User: us-east-1

Bot: VPC size? (Small, Medium, Big)
User: Small

... (continues for all fields)
```

---

### Step 3: Review Summary (T+2 min)

Both options show a summary:

```
┌─────────────────────────────────────────────┐
│  📋 Review Your Request                     │
├─────────────────────────────────────────────┤
│                                             │
│  Project Name: EMS                          │
│  Service: EMS API                           │
│  Environments: Dev, Prod                    │
│  Regions: us-east-1                         │
│  VPC Model: Small                           │
│  Terraform Repo: myorg/ems-infra           │
│  Team DL: team-ems@company.com             │
│  Team Channel: #team-ems                    │
│                                             │
│  Business Justification:                    │
│  New EMS service for Q3 launch             │
│                                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━        │
│                                             │
│  HCP Project: EMS                           │
│  Workspaces:                                │
│    • ems-wspace-dev                        │
│    • ems-wspace-prod                       │
│                                             │
│         [Cancel]         [Submit]           │
└─────────────────────────────────────────────┘
```

**User clicks [Submit]**

---

### Step 4: Submission Received (T+2 min)

**User sees:**
```
⏳ Processing your request...
```

**Behind the scenes:**
1. Slack bot validates basic input
2. Calls API Gateway endpoint
3. API Gateway triggers Step Functions

---

### Step 5: Workflow Started (T+2 min + 1 sec)

**User receives confirmation:**

```
✅ Onboarding workflow started!

Execution ID: 8f7a9c2e-1b3d-4f5e-9a8b-7c6d5e4f3a2b

The workflow is running in the background and will:
  1. ✓ Validate intake data
  2. ✓ Create GitHub branch
  3. ✓ Commit intake document
  4. ✓ Create HCP Terraform project
  5. ✓ Create Dev workspace
  6. ✓ Create Prod workspace
  7. ✓ Configure workspace variables

You'll receive a notification when complete (~30-45 seconds).

Check status: /aws-det-status 8f7a9c2e-1b3d-4f5e-9a8b-7c6d5e4f3a2b
```

---

### Step 6: Background Processing (T+2 min to T+2:45 min)

While user waits, the system executes:

#### Phase 1: Validation (2-5 seconds)

```
┌─────────────────────────────────┐
│  Lambda: validate_intake        │
├─────────────────────────────────┤
│  • Check required fields        │
│  • Validate formats             │
│  • Normalize data               │
│  • Create execution record      │
└─────────────────────────────────┘
```

**DynamoDB Record Created:**
```json
{
  "execution_id": "8f7a9c2e-...",
  "status": "RUNNING",
  "current_step": "ValidateIntake",
  "project_name": "EMS",
  "slack_channel": "C12345",
  "slack_user": "U67890",
  "created_at": "2026-06-07T10:00:00Z"
}
```

#### Phase 2: GitHub Operations (5-10 seconds)

**Lambda: github_branch**
```
┌─────────────────────────────────┐
│  Lambda: github_branch          │
├─────────────────────────────────┤
│  • Create branch: ems-onboard   │
│  • From: main                   │
│  • Branch created ✓             │
└─────────────────────────────────┘
```

**Lambda: github_commit**
```
┌─────────────────────────────────┐
│  Lambda: github_commit          │
├─────────────────────────────────┤
│  • Generate intake.yaml         │
│  • Commit to ems-onboard        │
│  • File: intake-files/ems.yaml  │
│  • Commit SHA: abc123... ✓      │
└─────────────────────────────────┘
```

#### Phase 3: HCP Project Creation (3-5 seconds)

```
┌─────────────────────────────────┐
│  Lambda: hcp_project            │
├─────────────────────────────────┤
│  • Project name: EMS            │
│  • Description: Auto-created    │
│  • Project ID: prj-abc123 ✓     │
└─────────────────────────────────┘
```

#### Phase 4: Workspace Creation - PARALLEL (10-15 seconds)

```
┌──────────────────────┐   ┌──────────────────────┐
│ Lambda: hcp_workspace│   │ Lambda: hcp_workspace│
│ Environment: Dev     │   │ Environment: Prod    │
├──────────────────────┤   ├──────────────────────┤
│ • Name: ems-wspace-dev│  │• Name: ems-wspace-prod│
│ • Execution: remote  │   │ • Execution: remote  │
│ • VCS: myorg/ems-infra│  │• VCS: myorg/ems-infra│
│ • Branch: ems-onboard│   │ • Branch: ems-onboard│
│ • ID: ws-dev123 ✓    │   │ • ID: ws-prod456 ✓   │
└──────────────────────┘   └──────────────────────┘
          ↓                            ↓
    (Runs simultaneously - 10-15 seconds total)
```

#### Phase 5: Variable Configuration - PARALLEL (5-10 seconds)

```
┌──────────────────────┐   ┌──────────────────────┐
│ Lambda: hcp_vars     │   │ Lambda: hcp_vars     │
│ Workspace: Dev       │   │ Workspace: Prod      │
├──────────────────────┤   ├──────────────────────┤
│ • environment=dev    │   │ • environment=prod   │
│ • region=us-east-1   │   │ • region=us-east-1   │
│ • vpc_model=small    │   │ • vpc_model=small    │
│ • project=ems        │   │ • project=ems        │
│ • Configured ✓       │   │ • Configured ✓       │
└──────────────────────┘   └──────────────────────┘
          ↓                            ↓
    (Runs simultaneously - 5-10 seconds total)
```

---

### Step 7: Completion Notification (T+2:45 min)

**Lambda: completion_notifier** sends message to Slack:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 Onboarding Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Project: EMS
Execution ID: 8f7a9c2e-1b3d-4f5e-9a8b-7c6d5e4f3a2b
Status: ✅ SUCCESS
Duration: 42 seconds

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📂 GitHub:
Branch: ems-onboard
Commit: abc123def456
File: https://github.com/myorg/ems-infra/blob/ems-onboard/intake-files/ems.yaml

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☁️  HCP Terraform:
Project: EMS (prj-abc123)
https://app.terraform.io/app/myorg/projects/prj-abc123

Workspaces Created:
✓ ems-wspace-dev (ws-dev123)
  https://app.terraform.io/app/myorg/workspaces/ems-wspace-dev
  
✓ ems-wspace-prod (ws-prod456)
  https://app.terraform.io/app/myorg/workspaces/ems-wspace-prod

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Next Steps:
1. Review intake document in GitHub
2. Create pull request: ems-onboard → main
3. Merge after approval
4. Run Terraform plans in HCP workspaces
5. Apply infrastructure changes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Started by: @john.doe
Completed at: 2026-06-07 10:02:42 UTC
```

---

### Step 8: User Takes Next Steps

**User can now:**

1. **Review GitHub Branch**
   - Visit branch link
   - Review intake.yaml file
   - Verify all settings

2. **Create Pull Request**
   - Open PR from ems-onboard to main
   - Get team review
   - Merge when approved

3. **Access HCP Workspaces**
   - Click workspace links
   - Review configurations
   - Run Terraform plans

4. **Deploy Infrastructure**
   - Queue Terraform plan
   - Review changes
   - Apply when ready

---

## Timeline Summary

| Time | Step | Duration | Component |
|------|------|----------|-----------|
| T+0 | User opens Slack | - | User |
| T+0-2min | Fill form/chat | 1-2 min | User |
| T+2min | Submit request | Instant | Slack Bot |
| T+2min | API call | <1 sec | API Gateway |
| T+2min | Start workflow | <1 sec | Step Functions |
| T+2-3min | Validate | 2-5 sec | Lambda |
| T+3-4min | GitHub ops | 5-10 sec | Lambda |
| T+4-5min | HCP project | 3-5 sec | Lambda |
| T+5-6min | Create workspaces | 10-15 sec | Lambda (parallel) |
| T+6-7min | Configure vars | 5-10 sec | Lambda (parallel) |
| T+7min | Send notification | 2-3 sec | Lambda |
| **Total** | **User to Ready** | **~2:45 min** | **End-to-End** |

**User active time:** 1-2 minutes  
**Automated processing:** 30-45 seconds  
**Total time:** ~2:45 minutes

---

## What Gets Created

### GitHub Resources
```
Repository: myorg/ems-infra
├── Branch: ems-onboard (from main)
│   └── intake-files/
│       └── ems.yaml
│           ├── project_name: EMS
│           ├── environments: [Dev, Prod]
│           ├── regions: [us-east-1]
│           ├── vpc_model: Small
│           ├── service_name: EMS API
│           └── ... (all intake data)
```

### HCP Terraform Resources
```
Organization: myorg
└── Project: EMS (prj-abc123)
    ├── Workspace: ems-wspace-dev (ws-dev123)
    │   ├── VCS Repo: myorg/ems-infra
    │   ├── Branch: ems-onboard
    │   ├── Working Dir: ./
    │   ├── Execution Mode: remote
    │   ├── Variables:
    │   │   ├── environment = "dev"
    │   │   ├── region = "us-east-1"
    │   │   ├── vpc_model = "small"
    │   │   └── project_name = "ems"
    │   └── Auto-apply: disabled
    │
    └── Workspace: ems-wspace-prod (ws-prod456)
        ├── VCS Repo: myorg/ems-infra
        ├── Branch: ems-onboard
        ├── Working Dir: ./
        ├── Execution Mode: remote
        ├── Variables:
        │   ├── environment = "prod"
        │   ├── region = "us-east-1"
        │   ├── vpc_model = "small"
        │   └── project_name = "ems"
        └── Auto-apply: disabled
```

### DynamoDB Record
```json
{
  "execution_id": "8f7a9c2e-1b3d-4f5e-9a8b-7c6d5e4f3a2b",
  "status": "SUCCEEDED",
  "project_name": "EMS",
  "slack_channel": "C12345",
  "slack_user": "U67890",
  "created_at": "2026-06-07T10:00:00Z",
  "completed_at": "2026-06-07T10:00:42Z",
  "steps": {
    "ValidateIntake": {"status": "SUCCEEDED"},
    "CreateGitHubBranch": {"status": "SUCCEEDED"},
    "CommitToGitHub": {"status": "SUCCEEDED"},
    "CreateHCPProject": {"status": "SUCCEEDED"},
    "CreateWorkspaces": {"status": "SUCCEEDED"},
    "ConfigureVariables": {"status": "SUCCEEDED"}
  },
  "result": {
    "github_branch": "ems-onboard",
    "github_commit_sha": "abc123def456",
    "hcp_project_id": "prj-abc123",
    "workspaces": {
      "Dev": {"id": "ws-dev123", "name": "ems-wspace-dev"},
      "Prod": {"id": "ws-prod456", "name": "ems-wspace-prod"}
    }
  }
}
```

---

## Error Handling

### Scenario: GitHub Rate Limit

**What happens:**
```
Step 2: CreateGitHubBranch fails
  ↓
Retry 1 (after 2 seconds)
  ↓
Retry 2 (after 4 seconds)
  ↓
Retry 3 (after 8 seconds)
  ↓
If still failing: Workflow fails
  ↓
User notified: "Failed at CreateGitHubBranch: Rate limit exceeded"
```

### Scenario: One Workspace Fails

**What happens:**
```
CreateWorkspaces (parallel):
  Dev: ✓ Success
  Prod: ✗ Failed (network timeout)
  ↓
Prod workspace retried (up to 3 times)
  ↓
If success: Continue normally
If fail: Workflow continues with partial success
  ↓
User notified: "Dev workspace created, Prod failed (see logs)"
```

---

## User Experience Highlights

### ✅ Instant Feedback
- Immediate confirmation after submission
- Execution ID for tracking
- Progress updates available

### ✅ Non-Blocking
- User not waiting for 45 seconds
- Can continue other work
- Notification when ready

### ✅ Transparency
- All steps visible in notification
- Links to all created resources
- Full audit trail in DynamoDB

### ✅ Error Recovery
- Automatic retries
- Clear error messages
- Partial success handled gracefully

### ✅ Self-Service
- No manual intervention needed
- Fully automated end-to-end
- User has all links to proceed

---

## Common User Paths

### Path 1: Perfect Flow
```
Submit → All steps succeed → Notification in 45 sec → User proceeds
```

### Path 2: Retry Recovery
```
Submit → GitHub fails → Auto-retry → Success → Notification
```

### Path 3: Partial Success
```
Submit → Dev works, Prod fails → Notification with partial success
→ User manually creates Prod workspace or resubmits
```

### Path 4: Validation Failure
```
Submit → Validation fails → Immediate error → User corrects → Resubmit
```

---

## Monitoring Your Request

### Check Status Anytime

```
/aws-det-status 8f7a9c2e-1b3d-4f5e-9a8b-7c6d5e4f3a2b
```

**Response:**
```
📊 Execution Status

ID: 8f7a9c2e-1b3d-4f5e-9a8b-7c6d5e4f3a2b
Status: RUNNING
Current Step: CreateWorkspaces
Started: 2026-06-07 10:00:00 UTC
Duration: 15 seconds

Progress:
✓ ValidateIntake
✓ CreateGitHubBranch
✓ CommitToGitHub
✓ CreateHCPProject
⏳ CreateWorkspaces (in progress)
⌛ ConfigureVariables (pending)
```

---

## Summary

The user journey is:
1. **Fast** - 2-3 minutes total, mostly user input
2. **Automated** - 30-45 seconds of hands-off processing
3. **Reliable** - Automatic retries and error handling
4. **Transparent** - Full visibility into progress and results
5. **Non-blocking** - User notified when ready, no waiting

**Result:** User goes from "I need infrastructure" to "ready to deploy" in under 3 minutes.

---

**That's the complete journey! 🚀**
