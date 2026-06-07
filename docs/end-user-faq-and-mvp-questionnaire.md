# DET Onboarding: End-User FAQ and MVP Questionnaire

This guide is for workload teams using the DET Slack bot onboarding flow. It explains what to expect in the current implementation and provides a clean questionnaire template you can complete and share.

Follow this [DOc for FAQ on Onboarding process](https://salesforce-sandbox2.enterprise.slack.com/docs/T04SR5XV56X/F0B2CDRBUBX).

## What to Expect in the Current Bot Flow

- Start in channel with `/aws-det-onboard`.
- The bot creates a starter message and expects follow-ups in that thread.
- The bot asks for missing details until intake is complete.
- Once complete, the bot shows a preview with `Approve`, `Open Form`, and `Cancel` buttons.
- You must click `Approve` to submit. Typing "approve" in chat is not accepted.
- After approval, the chat session is closed.

## Channel and DM Behavior (Important)

- In channels:
  - Use `/aws-det-onboard` to start.
  - Continue only in that thread.
  - Top-level channel messages are ignored by design.
- In direct messages (DMs):
  - Message events are handled, and the bot can continue the conversation.
- Channel allowlist can be enforced by platform config (`DET_ALLOWED_CHANNELS`). If your channel is not allowed, onboarding will not proceed there.

## What the Bot Actually Collects Today

The bot validates against these required fields:

- `project_name`
- `terraform_repo` (format `owner/repo`)
- `team_channel`
- `environments` (`Dev`, `QA`, `Prod`)
- `regions` (`us-east-1`, `us-west-2`, `eu-west-1`)
- `vpc_model` (`Small`, `Medium`, `Big`)
- `service_name`
- `business_justification`
- `team_dl` (email-like distribution list)

It may also collect optional values such as `members`, `workspace_mode`, and `workspace_names`.

## Safety and Submission Expectations

- `Cancel` ends the chat intake and does not write to GitHub or HCP Terraform.
- By default, environments commonly run in dry-run mode, where approval simulates writes without changing external systems.
- Real GitHub and HCP Terraform writes happen only after button approval and only when dry-run is disabled by platform operators.

## FAQ

### 1) Why did the bot not reply to my normal channel message?
Top-level channel messages are ignored. Start with `/aws-det-onboard` and reply in the created thread.

### 2) Can I mention the bot with `@botname` to start onboarding?
Not in the current implementation. Use `/aws-det-onboard` instead.

### 3) What if I type "approve" in text?
The bot will ask you to use the `Approve` button. Text approval is intentionally blocked.

### 4) Why am I being asked for details one by one?
The bot validates required fields and asks only for missing or invalid items.

### 5) Which regions are accepted?
`us-east-1`, `us-west-2`, and `eu-west-1`.

### 6) Which environments are accepted?
`Dev`, `QA`, and `Prod`.

### 7) What VPC sizes are accepted by the intake?
`Small`, `Medium`, and `Big`.

### 8) What does `Open Form` do?
It opens the modal-based intake flow so you can complete/edit details there.

### 9) What happens after I click `Approve`?
The bot re-validates intake and then runs the configured submission actions (dry-run or real write, depending on environment configuration).

### 10) Why does the bot say my session expired?
Sessions are in-memory and can expire or reset after process restarts. Start again with `/aws-det-onboard`.

## MVP Workload Onboarding Questionnaire (User Copy Template)

Use this section as a fillable template for workload teams.

---

### 1) AWS Accounts and Environments

**Platform capability**  
For MVP, each workload is provisioned three AWS accounts: `Dev`, `QA`, and `Prod`.

**Questions**
- Does this meet your requirements?

**Response**
- Meets requirement: Yes / No
- If No, what do you need instead:

---

### 2) Deployment Regions

**Platform capability**  
For MVP, supported regions are:
- `us-east-1` (Virginia)
- `us-west-2` (Oregon)
- `eu-west-1` (Dublin)

**Questions**
- Will your workload be single-region or multi-region?
- Which region(s) will you use?
- If multi-region, what is the primary driver (HA, DR, latency, residency, regulatory, other)?

**Response**
- Deployment model: Single region / Multiple regions
- Region(s):
- Multi-region reason (if applicable):

---

### 3) Workload-to-Workload Communication

**Platform capability**  
Private workload-to-workload (east-west) communication is supported.

**Questions**
- Does your workload communicate with other workloads/services?
- If yes, which ones?
- Is any communication cross-region?
- If yes, provide source region(s), destination region(s), and workload/service pairs.

**Response**
- Requires workload/service communication: Yes / No
- Target workloads/services: EMS / AMS / MLI / Other
- Cross-region communication: Yes / No
- Cross-region details (if applicable):

---

### 4) Private DNS for Inter-VPC Communication

**Platform capability**  
Private DNS records can be created in pre-created private hosted zones per account and region.

Naming conventions:
- Prod: `{appName}.{region}.internal.det.salesforce.com`
- Non-prod: `{appName}-{environment}.{region}.internal.det.salesforce.com`

**Questions**
- Do these naming conventions meet your requirements?
- If not, why?
- Do you need more than one internal endpoint per environment/region?

**Response**
- Naming convention acceptable: Yes / No
- If No, reason:
- Additional internal endpoints needed: Yes / No
- Details (if applicable):

---

### 5) Internal TLS Certificates

**Platform capability**  
Certificates have been requested for standard EMS internal FQDN patterns across supported regions/environments.

**Questions**
- Do these endpoint names satisfy your requirements?
- Do you need additional internal endpoint certificates?
- If yes, list additional FQDNs.

**Response**
- Existing internal cert naming acceptable: Yes / No
- Additional internal certs required: Yes / No
- Additional FQDNs (if applicable):

---

### 6) Private DNS for Intra-VPC Communication

**Platform capability**  
For intra-VPC communication, private DNS records can be created in:
- `local.det.salesforce.com`

**Questions**
- Does this meet your requirements?
- If not, what is needed instead?

**Response**
- Requirement met: Yes / No
- Additional requirements (if applicable):

---

### 7) GitHub Repositories and CI/CD Integration

**Platform capability**  
For MVP, workload repositories should be created and integrated with CI/CD pipelines during onboarding.

**Questions**
- Have repositories been created and integrated with CI/CD workflows?
- If not, when will this be completed?
- Have Terraform project/workflow steps in EP Blueprint been completed?

**Response**
- Repos integrated with CI/CD: Yes / No
- If No, expected completion date:
- EP Blueprint Terraform workflows completed: Yes / No
- Additional comments:

---

### 8) Public Endpoints and Public DNS

**Platform capability**  
If public endpoints are needed, accounts can use pre-created public hosted zone subdomains:
- `{appName}-{environment}.det.salesforce.com`

Perimeter team coordination is required for public exposure.

**Questions**
- Will the application expose public endpoints?
- If yes, will standard DNS pattern be used?
- What is Perimeter team coordination status?
- Any special public exposure requirements?

**Response**
- Public endpoints required: Yes / No
- Use standard public DNS pattern: Yes / No
- Perimeter coordination: Not started / In progress / Completed / Not applicable
- Special requirements (if applicable):

---

### 9) VPC Model, Sizing, and Pre-Created Subnets

**Platform capability**  
One pre-created VPC per region is provisioned during account vending.

Baseline subnet model per workload account:
- 3 private subnets (one per AZ)
- "4 equal blocks, use 3, keep 1 spare" model

Available options:
- `/24` VPC -> `3 x /26` private subnets (+ `1` spare `/26`)
- `/22` VPC -> `3 x /24` private subnets (+ `1` spare `/24`)
- `/20` VPC -> `3 x /22` private subnets (+ `1` spare `/22`)

Default expectation:
- Use `/24` unless larger size is justified.

**Questions**
- Is one-VPC-per-region acceptable?
- Are available VPC sizes and subnet layouts acceptable?
- Preferred VPC size by region/environment?
- Is 3 subnets + 1 spare sufficient?
- Provide sizing justification (required for larger than `/24`):
  - Expected compute nodes/instances
  - Pod/task density
  - Private endpoints/load balancers
  - Growth over time
- Any additional networking/subnetting/segmentation needs?

**Response**
- One VPC per region acceptable: Yes / No
- Available VPC size options acceptable: Yes / No
- Baseline subnet layout acceptable: Yes / No
- Preferred VPC size by region/environment:
- VPC size justification:
- Additional networking/subnetting/segmentation needs:

---

### 10) Identity and Access Management (IAM)

**Platform capability**  
After account provisioning, default AWS Entitlements are synced to EIP for request-based console/CLI access.

Access notes:
- Entitlements may take up to 24 hours post-provisioning to appear in EIP.
- High-risk entitlements need manager plus Entitlement Owner approvals.
- Entitlement Owners handle quarterly access reviews (QARs).
- Console/CLI access is intentionally constrained; Terraform + CI/CD is the preferred delivery model.

**Questions**
- Who will own high-risk Entitlements and perform QARs?
- Who needs membership in high-risk Entitlements?

**Response**
- Entitlement Owner(s) (manager/senior team members):
- Members requiring high-risk entitlement access:
- Additional IAM requirements/blockers (service + use case + why console/CLI needed):

---

## Recommended Submission Format to Avoid Back-and-Forth

When answering the questionnaire, provide complete responses in one pass. This reduces clarification loops and speeds up onboarding decisions.

