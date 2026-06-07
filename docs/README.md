# 📚 DET AWS CI/CD Onboarding - Documentation

Welcome to the documentation directory! All project documentation is organized here.

---

## 📖 Table of Contents

### Getting Started
- **[QUICK_START.md](QUICK_START.md)** - Quick setup guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment instructions
- **[USER_JOURNEY.md](USER_JOURNEY.md)** - Step-by-step user workflow (19 Lambda executions detailed)

### Architecture & Design
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Overview of serverless refactoring
- **[step-functions-architecture.md](step-functions-architecture.md)** - Step Functions technical architecture
- **[MODULAR_RESTRUCTURE.md](MODULAR_RESTRUCTURE.md)** - Terraform modular architecture details
- **[FINAL_MODULE_SUMMARY.md](FINAL_MODULE_SUMMARY.md)** - Complete module deployment guide

### Component Details
- **[LAMBDA_FUNCTIONS_MAPPING.md](LAMBDA_FUNCTIONS_MAPPING.md)** - What each Lambda function does
- **[DYNAMODB_TRACKING_README.md](DYNAMODB_TRACKING_README.md)** - DynamoDB status tracking quick guide
- **[dynamodb-status-tracking.md](dynamodb-status-tracking.md)** - Complete DynamoDB schema and usage

### Security & Configuration
- **[TOKEN_STORAGE_GUIDE.md](TOKEN_STORAGE_GUIDE.md)** - Token security and management

### Migration & Cleanup
- **[REORGANIZATION_COMPLETE.md](REORGANIZATION_COMPLETE.md)** - Lambda functions reorganization details
- **[MIGRATION_CLEANUP_GUIDE.md](MIGRATION_CLEANUP_GUIDE.md)** - Migration guide from old to new architecture
- **[CLEANUP_COMPLETED.md](CLEANUP_COMPLETED.md)** - Summary of cleanup actions

### Project History
- **[CHANGELOG.md](CHANGELOG.md)** - Version history (1.0.0 → 2.0.0)
- **[FINAL_DELIVERABLES.md](FINAL_DELIVERABLES.md)** - Complete package summary

---

## 🎯 Quick Navigation by Role

### For Developers
Start here to understand the codebase:
1. [QUICK_START.md](QUICK_START.md) - Get up and running
2. [LAMBDA_FUNCTIONS_MAPPING.md](LAMBDA_FUNCTIONS_MAPPING.md) - What each function does
3. [step-functions-architecture.md](step-functions-architecture.md) - How orchestration works
4. [MODULAR_RESTRUCTURE.md](MODULAR_RESTRUCTURE.md) - Terraform module structure

### For DevOps/SRE
Deploy and manage infrastructure:
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment instructions
2. [FINAL_MODULE_SUMMARY.md](FINAL_MODULE_SUMMARY.md) - Module deployment guide
3. [TOKEN_STORAGE_GUIDE.md](TOKEN_STORAGE_GUIDE.md) - Security setup
4. [dynamodb-status-tracking.md](dynamodb-status-tracking.md) - Monitoring and logs

### For Product/Business
Understand the workflow:
1. [USER_JOURNEY.md](USER_JOURNEY.md) - Complete user experience
2. [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) - Benefits of new architecture
3. [CHANGELOG.md](CHANGELOG.md) - Version history and improvements

### For New Team Members
Onboarding reading order:
1. [QUICK_START.md](QUICK_START.md) - Quick introduction
2. [USER_JOURNEY.md](USER_JOURNEY.md) - How the system works
3. [LAMBDA_FUNCTIONS_MAPPING.md](LAMBDA_FUNCTIONS_MAPPING.md) - Component overview
4. [MODULAR_RESTRUCTURE.md](MODULAR_RESTRUCTURE.md) - Infrastructure architecture

---

## 📂 Documentation Categories

### 🚀 Setup & Deployment (3 docs)
- QUICK_START.md
- DEPLOYMENT.md
- FINAL_MODULE_SUMMARY.md

### 🏗️ Architecture & Design (3 docs)
- REFACTORING_SUMMARY.md
- step-functions-architecture.md
- MODULAR_RESTRUCTURE.md

### 🔧 Component Documentation (3 docs)
- LAMBDA_FUNCTIONS_MAPPING.md
- DYNAMODB_TRACKING_README.md
- dynamodb-status-tracking.md

### 🔐 Security (1 doc)
- TOKEN_STORAGE_GUIDE.md

### 📖 User Guides (1 doc)
- USER_JOURNEY.md

### 🔄 Migration & History (4 docs)
- REORGANIZATION_COMPLETE.md
- MIGRATION_CLEANUP_GUIDE.md
- CLEANUP_COMPLETED.md
- CHANGELOG.md

### 📦 Summaries (1 doc)
- FINAL_DELIVERABLES.md

**Total: 16 documentation files**

---

## 🔍 Find Documentation by Topic

### Infrastructure as Code
- [MODULAR_RESTRUCTURE.md](MODULAR_RESTRUCTURE.md)
- [FINAL_MODULE_SUMMARY.md](FINAL_MODULE_SUMMARY.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)

### Lambda Functions
- [LAMBDA_FUNCTIONS_MAPPING.md](LAMBDA_FUNCTIONS_MAPPING.md)
- [REORGANIZATION_COMPLETE.md](REORGANIZATION_COMPLETE.md)

### Step Functions
- [step-functions-architecture.md](step-functions-architecture.md)
- [USER_JOURNEY.md](USER_JOURNEY.md)

### DynamoDB
- [DYNAMODB_TRACKING_README.md](DYNAMODB_TRACKING_README.md)
- [dynamodb-status-tracking.md](dynamodb-status-tracking.md)

### API Gateway
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [USER_JOURNEY.md](USER_JOURNEY.md)

### Security & Tokens
- [TOKEN_STORAGE_GUIDE.md](TOKEN_STORAGE_GUIDE.md)

### Project Evolution
- [CHANGELOG.md](CHANGELOG.md)
- [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)
- [MIGRATION_CLEANUP_GUIDE.md](MIGRATION_CLEANUP_GUIDE.md)

---

## 📊 Documentation Stats

- **Total Files:** 16 markdown documents
- **Total Pages:** ~150 pages (estimated)
- **Coverage:**
  - Architecture: ✅ Complete
  - Setup: ✅ Complete
  - Components: ✅ Complete
  - Security: ✅ Complete
  - Migration: ✅ Complete
  - User Guides: ✅ Complete

---

## 🔗 Related Documentation

### In terraform/ directory:
- `../terraform/README.md` - Terraform-specific documentation
- `../terraform/SETUP_INSTRUCTIONS.md` - Detailed Terraform setup

### In project root:
- `../README.md` - Main project README
- `../start_slack_bot.sh` - Slack bot startup script

### In src/ directory:
- `../src/deprecated/README.md` - Deprecated code explanation

---

## 📝 Documentation Conventions

### File Naming
- `SCREAMING_SNAKE_CASE.md` - Major documentation (USER_JOURNEY.md)
- `kebab-case.md` - Technical specs (step-functions-architecture.md)

### Document Structure
1. **Title** - Clear, descriptive
2. **Introduction** - What this doc covers
3. **Sections** - Organized with headers
4. **Examples** - Code snippets, commands
5. **References** - Links to related docs

### Markdown Features Used
- ✅ Checkboxes for task lists
- 📦 Emojis for visual clarity
- `code blocks` for commands and code
- Tables for comparisons
- Links between documents

---

## 🤝 Contributing to Documentation

### Adding New Documentation
1. Create `.md` file in `docs/`
2. Follow naming conventions
3. Add entry to this README.md
4. Link from related docs

### Updating Existing Documentation
1. Edit the relevant `.md` file
2. Update "Last Updated" date
3. Add to CHANGELOG.md if significant

### Documentation Standards
- Keep docs up-to-date with code changes
- Use clear, concise language
- Include examples and code snippets
- Link to related documentation
- Update this README when adding/removing docs

---

## 🔄 Keep Documentation Updated

When you:
- Add a new Lambda function → Update `LAMBDA_FUNCTIONS_MAPPING.md`
- Change Step Functions → Update `step-functions-architecture.md`
- Modify Terraform → Update `MODULAR_RESTRUCTURE.md`
- Add a feature → Update `CHANGELOG.md`
- Change deployment → Update `DEPLOYMENT.md`

---

## 📞 Questions?

If you can't find what you're looking for:
1. Check the [Table of Contents](#-table-of-contents)
2. Search by [Topic](#-find-documentation-by-topic)
3. Browse by [Role](#-quick-navigation-by-role)
4. Review [Related Documentation](#-related-documentation)

---

**Documentation Status:** ✅ Complete  
**Last Updated:** June 5, 2026  
**Maintained By:** DET Platform Team
