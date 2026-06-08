# AWS DET Onboarding Bot - Documentation

Welcome to the AWS DET (DevOps Engineering Team) Onboarding Bot documentation.

## 📚 Documentation Overview

This documentation covers the complete AWS infrastructure onboarding workflow, from Slack bot interaction to automated resource provisioning via Step Functions and Lambda.

---

## 📖 Available Documents

1. **[QUICK_START.md](QUICK_START.md)** - Get started in 10 minutes
2. **[USER_JOURNEY.md](USER_JOURNEY.md)** - Complete user workflow walkthrough
3. **[AI_ORCHESTRATION.md](AI_ORCHESTRATION.md)** - AI-powered chat interface guide
4. **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and flow diagram
5. **README.md** (this file) - Documentation index

---

## 🎯 Quick Navigation

### For New Users
Start here to understand how to use the system:
1. [USER_JOURNEY.md](USER_JOURNEY.md) - Learn the complete workflow
2. [AI_ORCHESTRATION.md](AI_ORCHESTRATION.md) - Use the chat interface

### For Developers
Deploy and understand the system:
1. [QUICK_START.md](QUICK_START.md) - Deploy in 10 minutes
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Understand the technical flow

### For Product/Business
Understand the business value:
1. [USER_JOURNEY.md](USER_JOURNEY.md) - See the complete user experience
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Understand automation benefits

---

## 🚀 What This System Does

The AWS DET Onboarding Bot automates the complete infrastructure provisioning workflow:

**Input** → User fills a Slack form with project requirements

**Processing** → Automated workflow creates:
- GitHub branch with infrastructure documentation
- HCP Terraform project
- Terraform workspaces (Dev, QA, Prod)
- Workspace variables and configurations

**Output** → Fully configured infrastructure ready for deployment

---

## 🏗️ Architecture Overview

```
Slack User
    ↓
/aws-det-poc (form) or /aws-det-onboard (chat)
    ↓
API Gateway
    ↓
Step Functions (orchestration)
    ↓
Lambda Functions (execution)
    ↓
DynamoDB (tracking)
    ↓
GitHub + HCP Terraform (provisioning)
    ↓
Slack Notification (completion)
```

---

## 💡 Two Ways to Use

### 1. Form-Based (Traditional)
Command: `/aws-det-poc`
- Opens a structured form in Slack
- Fill out all fields
- Submit for processing

### 2. Chat-Based (AI-Powered)
Command: `/aws-det-onboard`
- Natural language conversation
- AI extracts requirements from chat
- Review and approve before submission

Details in [AI_ORCHESTRATION.md](AI_ORCHESTRATION.md)

---

## 📊 System Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| Slack Bot | User interface | Python + Slack Bolt |
| API Gateway | Entry point | AWS API Gateway |
| Step Functions | Workflow orchestration | AWS Step Functions |
| Lambda Functions | Task execution | Python 3.12 |
| DynamoDB | Status tracking | AWS DynamoDB |
| GitHub | Documentation storage | GitHub API |
| HCP Terraform | Infrastructure management | Terraform Cloud API |

---

## 🔑 Key Features

✅ **Automated Workflow** - End-to-end infrastructure provisioning  
✅ **Parallel Execution** - Multiple workspaces created simultaneously  
✅ **Error Recovery** - Automatic retries with exponential backoff  
✅ **Status Tracking** - Real-time progress updates in DynamoDB  
✅ **Slack Integration** - Start and monitor from Slack  
✅ **AI Chat Interface** - Natural language requirements gathering  
✅ **Audit Trail** - Complete execution history and logs  
✅ **Cost Efficient** - Pay only for what you use (~$2.24/month for 1000 requests)

---

## 📈 Typical Workflow Duration

| Step | Duration | Notes |
|------|----------|-------|
| Form submission | 1-2 min | User fills form |
| Validation | 2-5 sec | Intake validation |
| GitHub operations | 5-10 sec | Branch + commit |
| HCP project creation | 3-5 sec | Create project |
| Workspace creation | 10-15 sec | Parallel execution (Dev, QA, Prod) |
| Variable configuration | 5-10 sec | Parallel execution |
| **Total** | **~30-45 sec** | Automated execution time |

---

## 🛠️ Prerequisites

To deploy and use this system:

**AWS Requirements:**
- AWS account with appropriate permissions
- AWS CLI configured
- Terraform 1.5+ installed

**Service Tokens:**
- GitHub Personal Access Token (repo scope)
- HCP Terraform Token (organization access)
- Slack Bot Token (bot, commands, chat:write scopes)
- Slack App Token (connections:write for socket mode)

**Configuration:**
- Slack app configured with slash commands
- OAuth tokens for VCS integration
- DynamoDB tables created
- Lambda execution roles configured

---

## 📞 Getting Help

1. **Quick Start Issues** → Check [QUICK_START.md](QUICK_START.md) troubleshooting section
2. **User Workflow Questions** → See [USER_JOURNEY.md](USER_JOURNEY.md) step-by-step guide
3. **AI Chat Issues** → Review [AI_ORCHESTRATION.md](AI_ORCHESTRATION.md) chat guide
4. **Technical Issues** → Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design

---

## 🔄 System Status

**Current Version:** 2.0.0  
**Architecture:** Serverless (API Gateway + Step Functions + Lambda)  
**Status:** ✅ Production Ready  
**Last Updated:** June 7, 2026  
**Maintained By:** DET Platform Team

---

## 📝 Document Index

| Document | Purpose | Audience |
|----------|---------|----------|
| README.md | Overview and navigation | Everyone |
| QUICK_START.md | Setup and deployment | DevOps, Developers |
| USER_JOURNEY.md | Complete user workflow | Users, Product |
| AI_ORCHESTRATION.md | Chat interface guide | Users |
| ARCHITECTURE.md | Technical architecture | Developers, Architects |

---

## 🎯 Next Steps

**If you're a user:** Start with [USER_JOURNEY.md](USER_JOURNEY.md)  
**If you're deploying:** Start with [QUICK_START.md](QUICK_START.md)  
**If you're developing:** Start with [ARCHITECTURE.md](ARCHITECTURE.md)

---

**Happy Onboarding! 🚀**
