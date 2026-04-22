<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# Automating 10DLC Registration with AWS End User Messaging SMS

## The Challenge

If you're sending SMS messages to US recipients using 10-digit long codes (10DLC), you know the registration process is essential — but it's also complex, multi-step, and slow.

Here's what the process looks like today:

1. Register your company (brand) with the Campaign Registry
2. Wait for brand approval (24-48 hours)
3. Optionally apply for brand vetting to increase throughput ($40 fee, takes a few business days)
4. Register your messaging campaign with details about your use case, opt-in process, and sample messages
5. Wait for campaign approval (4-6 weeks due to manual carrier review)
6. Request a 10DLC phone number
7. Associate the phone number with your approved campaign
8. Wait for carrier review of the association (4-6 more weeks)

Each step depends on the previous one completing successfully. If anything gets rejected, you need to fix it and resubmit — and the clock resets.

For organizations managing a handful of registrations, this is manageable through the AWS console. But if you're an ISV onboarding multiple customers, a large enterprise with many brands and campaigns, or simply want to eliminate the manual overhead, the process becomes a bottleneck.

The core problems are:

- **It's manual and sequential.** Each step requires human action after the previous step completes. If someone is on vacation or misses a notification, the process stalls.
- **It takes weeks.** End-to-end, a single 10DLC registration can take 8-12 weeks. Multiply that by dozens of brands or campaigns and you have a serious operational burden.
- **There's no built-in automation.** The AWS APIs support programmatic registration, but there's no out-of-the-box workflow that chains the steps together and handles the async wait times.
- **Rejections require intervention.** When a registration is rejected (common for incomplete opt-in workflows or mismatched campaign details), someone needs to notice, diagnose the issue, fix it, and resubmit.

## The Solution

This solution automates the entire 10DLC registration lifecycle using AWS serverless services. Instead of manually monitoring each step and triggering the next one, you submit a single form and the system handles everything — including waiting weeks for approvals and alerting you when something needs attention.

### How It Works

**You fill out one form.** A web-based wizard collects all the information needed for brand registration, campaign registration, and phone number provisioning in a single session. You upload your opt-in screenshot and any supporting documents right in the form.

**The system takes over.** When you submit, the solution:

- Creates your brand registration and submits it for approval
- Waits — not by polling, but by listening for real-time status change events from AWS End User Messaging SMS via Amazon EventBridge
- When the brand is approved, automatically creates and submits the vetting request (if you opted in)
- When vetting completes, automatically creates the campaign registration, populates all the fields, attaches your uploaded documents, and submits
- When the campaign is approved, automatically requests a 10DLC phone number and associates it with the campaign
- Sends you an email notification when everything is complete

**If something gets rejected, you get notified immediately.** The system sends an email with the registration ID and what needs to be fixed. The workflow pauses and waits for you to make corrections in the AWS console. Once you've fixed the issue and resubmitted, the workflow automatically picks back up when the registration status changes — or you can manually resume it via an API call.

### What This Means for You

| Without Automation | With Automation |
|---|---|
| Log into the console after each approval to start the next step | Submit once, the system handles all subsequent steps |
| Manually check registration status daily/weekly | Real-time EventBridge notifications — no polling |
| Risk of delays if someone misses an approval notification | Automatic progression within minutes of each approval |
| No visibility into where things stand across multiple registrations | DynamoDB table tracks every registration's current state |
| Rejections can go unnoticed for days | Immediate email alert with details on what needs fixing |
| Each registration requires ~30 minutes of manual API/console work spread over weeks | ~5 minutes to fill out the form, then hands-off |

## What's Included

### Registration Wizard (Front End)

A browser-based form that walks you through every required field for brand and campaign registration. It's organized into logical steps:

1. Company information (legal name, tax ID, address)
2. Contact information (DBA name, website, support email/phone)
3. Vetting preference (opt-in or skip)
4. Campaign details (description, opt-in workflow, T&C, privacy policy, HELP/STOP messages)
5. Use case and compliance (message type, use case category, embedded links, age-gating)
6. Message samples (1-5 example messages you plan to send)

Every field shows the exact API field path and validation rules, so you know exactly what's expected. File uploads (opt-in screenshots, T&C documents, privacy policies) go directly from your browser to a private S3 bucket — no data passes through intermediate servers.

### Automated Workflow (Back End)

An AWS Step Functions state machine that orchestrates the entire registration process. It uses a "wait for callback" pattern — the workflow pauses at each approval step and resumes automatically when EventBridge delivers a status change event from AWS End User Messaging SMS.

The workflow handles:
- Brand registration creation, field population, and submission
- Brand vetting (optional) with proper association ordering
- Campaign registration with all fields, attachments, and compliance acknowledgements
- Phone number provisioning and campaign association
- Rejection handling with human-in-the-loop notifications
- Timeout handling (configurable, defaults to 30 days per wait state)

### Notification System

Amazon SNS delivers email alerts for:
- Registration completions (brand approved, campaign approved, fully complete)
- Rejections that need human intervention (with the registration ID and instructions)
- Vetting failures (non-blocking — the workflow continues with standard throughput)
- Timeouts (if a registration hasn't been reviewed within the timeout period)

### Status Tracking

Every registration request is tracked in a DynamoDB table with:
- Current workflow state
- All registration IDs (brand, vetting, campaign, phone number)
- Timestamps for each state transition
- The original form data (for audit and retry purposes)

## Deployment

The entire solution is packaged as an AWS SAM (Serverless Application Model) template. Deployment is two commands:

```
sam build
sam deploy --guided
```

SAM will prompt you for a stack name, AWS region, notification email, and CORS origin. All infrastructure — DynamoDB table, S3 bucket, Lambda functions, Step Functions state machine, EventBridge rule, SNS topic, and API Gateway — is created automatically.

There are no servers to manage, no infrastructure to maintain, and you only pay for what you use. Idle wait states in Step Functions (which is most of the registration lifecycle) cost nothing.

## Requirements

- An AWS account with AWS End User Messaging SMS enabled
- AWS CLI and SAM CLI installed (for deployment)
- A valid email address for notifications
- Your company's registration details (legal name, EIN/tax ID, address, website)
- An opt-in workflow description and screenshot showing how users consent to receive messages
- At least one sample message that reflects what you plan to send

## Frequently Asked Questions

**Can I use this for multiple brands or campaigns?**
Yes. Each form submission creates an independent workflow. You can have as many in-flight registrations as you need.

**What happens if I need to change something after submission?**
The workflow is designed to handle rejections gracefully. If a registration is rejected, you'll get an email notification. Fix the issue in the AWS console, resubmit, and the workflow will automatically resume when the status changes.

**Does this replace the AWS console?**
For the initial registration, yes — you fill out the wizard instead of the console. For handling rejections or making post-submission changes, you'll still use the AWS console to edit and resubmit the registration.

**What are the costs?**
The infrastructure costs are minimal (a few cents per registration for Lambda, DynamoDB, and Step Functions). The main costs are the EUM SMS registration fees themselves — a one-time brand registration fee, $40 for optional vetting, a monthly campaign fee, and a monthly phone number lease. See [AWS End User Messaging Pricing](https://aws.amazon.com/end-user-messaging/pricing/) for current rates.

**How long does the full process take?**
The same as manual registration — the bottleneck is the carrier review process (4-6 weeks for campaigns). The difference is that you don't need to manually trigger each step. The automation eliminates the gaps between approvals and next actions, which can save days or weeks of elapsed time.

**Is my data secure?**
This solution includes security controls such as time-limited presigned URLs, encrypted Amazon S3 storage with TLS enforcement, per-function IAM roles, and Amazon DynamoDB encryption at rest. Under the [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/), AWS manages the security of the cloud infrastructure, and you are responsible for security in the cloud. This means you must review IAM policies, restrict CORS origins, enable AWS CloudTrail logging, add API authentication, and perform your own security assessment before production use. See the Security section in the README for the full list of customer responsibilities.
