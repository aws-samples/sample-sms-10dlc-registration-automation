# 10DLC Registration Automation

Automated 10DLC registration pipeline using AWS Step Functions, EventBridge, Lambda, DynamoDB, and S3. Handles the full lifecycle — brand registration, optional vetting, campaign registration, phone number provisioning, and association — with event-driven callbacks and human-in-the-loop for rejections.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Front End   │────▶│ API Gateway  │────▶│  Lambda      │────▶│  DynamoDB       │
│  (Wizard)    │     │  (HTTP API)  │     │  (Intake)    │     │  (Registrations)│
└─────────────┘     └─────────────┘     └──────┬───────┘     └─────────────────┘
       │                                        │
       │  presigned URL                         ▼
       │  upload ──────▶ S3 Bucket     ┌──────────────────┐
       │                (Staging)      │  Step Functions   │
       │                               │  State Machine    │
       │                               │                   │
       │                               │  1. Create Brand  │
       │                               │  2. Wait ◀──────── EventBridge
       │                               │  3. Vet Brand     │  (Registration
       │                               │  4. Wait ◀────────│   Status Change)
       │                               │  5. Create Camp.  │
       │                               │  6. Wait ◀────────│
       │                               │  7. Request Phone │
       │                               │  8. Associate     │
       │                               │  9. Complete      │
       │                               └────────┬─────────┘
       │                                        │
       │                               ┌────────▼─────────┐
       │                               │  SNS             │
       │                               │  (Notifications)  │
       │                               └──────────────────┘
```

A full draw.io architecture diagram is available at `documentation/architecture/10dlc-registration-automation-system-architecture.drawio`.

## How It Works

### End-to-End Flow

1. User fills out the registration wizard (static HTML front end)
2. Files (opt-in screenshot, T&C, privacy policy) upload directly to S3 via presigned URLs — no file data flows through API Gateway or Lambda
3. Form submission hits `POST /api/submit` → Intake Lambda → writes all form data to DynamoDB → starts a Step Functions execution
4. Step Functions orchestrates the multi-step, multi-week registration process:

| Step | Action | Wait? | Duration |
|------|--------|-------|----------|
| 1 | Create brand registration, populate fields, submit | Yes — `waitForTaskToken` | 24-48 hours |
| 2 | (Optional) Create brand vetting, associate brand, submit | Yes — `waitForTaskToken` | A few business days |
| 3 | Create campaign registration, associate brand, populate fields + attachments, submit | Yes — `waitForTaskToken` | 4-6 weeks |
| 4 | Request 10DLC phone number, associate with campaign | No | Immediate |
| 5 | Send completion notification | No | Immediate |

5. EventBridge captures `Registration Status Change` events from AWS End User Messaging SMS
6. Event Router Lambda receives the event, looks up the corresponding task token in DynamoDB (via GSI on registration ID), and calls `SendTaskSuccess` or `SendTaskFailure` to resume the Step Functions execution
7. On rejection (`REQUIRES_UPDATES`), the workflow notifies the operator via SNS and pauses at a human-in-the-loop wait state
8. On completion, sends a success notification via SNS

### EventBridge Integration

AWS End User Messaging SMS emits `Registration Status Change` events to EventBridge for these statuses:

| Status | Meaning | Action Taken |
|--------|---------|--------------|
| `CREATED` | Registration created | Ignored (in progress) |
| `SUBMITTED` | Registration submitted for review | Ignored (in progress) |
| `REVIEWING` | Under third-party review | Ignored (in progress) |
| `COMPLETE` | Approved | `SendTaskSuccess` → workflow continues |
| `REQUIRES_UPDATES` | Rejected, needs fixes | `SendTaskFailure` → human-in-the-loop |
| `REQUIRES_AUTHENTICATION` | Brand email auth needed | `SendTaskFailure` → human-in-the-loop |
| `PROVISIONING` | Being provisioned | `SendTaskSuccess` → workflow continues |
| `CLOSED` | Registration closed | `SendTaskFailure` → workflow fails |
| `DELETED` | Registration deleted | `SendTaskFailure` → workflow fails |

### Human-in-the-Loop (Rejection Handling)

When a registration is rejected:

1. Step Functions catches the `TaskFailed` error and branches to the rejection path
2. Notification Lambda sends an SNS alert with the request ID, rejection reason, and instructions
3. The workflow enters another `waitForTaskToken` state, pausing indefinitely
4. The operator fixes the registration in the AWS console and resubmits
5. **Option A:** The EventBridge callback fires again when the registration status changes to `COMPLETE`, automatically resuming the workflow
6. **Option B:** The operator calls `POST /api/resume/{requestId}` to manually resume the workflow

### File Upload Flow (Presigned URLs)

1. Front end calls `POST /api/upload-url` with `{ fileName, contentType, fieldName, requestId }`
2. Lambda validates file type (PNG/JPEG/PDF only) and generates a presigned S3 PUT URL scoped to `uploads/{requestId}/{fieldName}.ext`, valid for 10 minutes
3. Front end uploads directly to S3 using the presigned URL — the file goes straight from the browser to S3
4. Front end stores the S3 key in the form state and includes it in the submission payload
5. Later, the Campaign Registration Lambda calls `create-registration-attachment --attachment-url s3://bucket/uploads/...` to create the EUM SMS attachment from the staged file

### Association Rules (from the API)

The 10DLC registration types have specific association ordering requirements:

| Registration Type | Associated Resource | Behavior |
|---|---|---|
| `US_TEN_DLC_BRAND_VETTING` | Brand registration | `ASSOCIATE_BEFORE_SUBMIT` |
| `US_TEN_DLC_CAMPAIGN_REGISTRATION` | Brand registration | `ASSOCIATE_BEFORE_SUBMIT` |
| `US_TEN_DLC_CAMPAIGN_REGISTRATION` | TEN_DLC phone number | `ASSOCIATE_AFTER_COMPLETE` |

The Step Functions workflow enforces this ordering automatically.

## Project Structure

```
10dlc-registration-automation/
├── frontend/                        # Static front end
│   └── 10dlc-registration-wizard.html
├── lambda/                          # Lambda function code
│   ├── intake/app.py                # API → DynamoDB → Start Step Functions
│   ├── presigned_url/app.py         # S3 presigned URL generator
│   ├── brand_registration/app.py    # Create + populate + submit brand
│   ├── vetting/app.py               # Create + associate + submit vetting
│   ├── campaign_registration/app.py # Create + populate + submit campaign
│   ├── phone_number/app.py          # Request phone + associate with campaign
│   ├── event_router/app.py          # EventBridge → task token → SFN callback
│   ├── notification/app.py          # SNS alerts for all status changes
│   └── resume/app.py                # Human-in-the-loop resume endpoint
├── statemachine/                    # Step Functions definition
│   └── registration_workflow.asl.json
├── documentation/
│   ├── architecture/
│   │   └── 10dlc-registration-automation-system-architecture.drawio
│   └── 10dlc-programmatic-registration-guide.md
├── template.yaml                    # SAM template (all infrastructure)
└── README.md
```

## Lambda Functions

| Function | Trigger | Purpose |
|----------|---------|---------|
| `IntakeFunction` | `POST /api/submit` | Writes form data to DynamoDB, starts Step Functions execution |
| `PresignedUrlFunction` | `POST /api/upload-url` | Generates time-limited S3 PUT URLs for direct browser uploads |
| `BrandRegistrationFunction` | Step Functions | Creates brand registration, populates all `companyInfo.*` and `contactInfo.*` fields, submits. Also stores task tokens for EventBridge callbacks. |
| `VettingFunction` | Step Functions | Creates vetting registration, associates brand, submits |
| `CampaignRegistrationFunction` | Step Functions | Creates campaign, associates brand, populates all `campaignInfo.*`, `campaignCapabilities.*`, `campaignUseCase.*`, `messageSamples.*` fields, creates attachments from S3, submits |
| `PhoneNumberFunction` | Step Functions | Requests a TEN_DLC phone number, associates with approved campaign |
| `EventRouterFunction` | EventBridge | Receives `Registration Status Change` events, looks up task tokens in DynamoDB via GSI, calls `SendTaskSuccess` or `SendTaskFailure` |
| `NotificationFunction` | Step Functions | Sends SNS alerts for completions, rejections, timeouts |
| `ResumeFunction` | `POST /api/resume/{requestId}` | Human-in-the-loop endpoint — looks up pending task token, calls `SendTaskSuccess` to resume workflow |

## DynamoDB Schema

### Table: `{StackName}-registrations`

| Attribute | Type | Description |
|-----------|------|-------------|
| `requestId` (PK) | String | Unique registration request ID (UUID) |
| `status` | String | Current workflow state (e.g., `BRAND_SUBMITTED`, `CAMPAIGN_PENDING`) |
| `enableVetting` | Boolean | Whether brand vetting was requested |
| `brandFields` | Map | All brand registration form data |
| `campaignFields` | Map | All campaign registration form data |
| `attachments` | Map | S3 keys for uploaded files (e.g., `{ "optInScreenshot": "uploads/req-abc/optInScreenshot.png" }`) |
| `phoneConfig` | Map | Phone number configuration (messageType, capabilities) |
| `brandRegId` | String | EUM SMS brand registration ID (populated after creation) |
| `campaignRegId` | String | EUM SMS campaign registration ID (populated after creation) |
| `vettingRegId` | String | EUM SMS vetting registration ID (populated after creation) |
| `phoneNumberId` | String | EUM SMS phone number ID (populated after provisioning) |
| `phoneNumber` | String | E.164 phone number (populated after provisioning) |
| `attachmentIds` | Map | EUM SMS attachment IDs (populated after `create-registration-attachment`) |
| `taskTokens` | Map | Step Functions task tokens keyed by wait state (e.g., `{ "brand": "token...", "campaign": "token..." }`) |
| `createdAt` | String | ISO 8601 timestamp |
| `updatedAt` | String | ISO 8601 timestamp |

### Global Secondary Indexes

| Index | Partition Key | Purpose |
|-------|--------------|---------|
| `brand-reg-index` | `brandRegId` | Look up request by brand registration ID (for EventBridge routing) |
| `campaign-reg-index` | `campaignRegId` | Look up request by campaign registration ID (for EventBridge routing) |

## API Endpoints

All endpoints are served via Amazon API Gateway HTTP API.

### `POST /api/submit`

Submit a complete registration request. Starts the automated workflow.

**Request body:**
```json
{
  "enableVetting": true,
  "brandFields": {
    "companyName": "Example Corp",
    "taxIdIssuingCountry": "US",
    "taxId": "123456789",
    "legalType": "PRIVATE_PROFIT",
    "address": "123 Main Street",
    "city": "Seattle",
    "state": "WA",
    "zipCode": "98101",
    "isoCountryCode": "US",
    "dbaName": "Example Corp",
    "contactVertical": "TECHNOLOGY",
    "website": "https://www.example.com",
    "supportEmail": "support@example.com",
    "supportPhoneNumber": "+12065550142"
  },
  "campaignFields": {
    "campaignName": "Example Corp OTP messages for account verification...",
    "campaignVertical": "TECHNOLOGY",
    "termsAndConditionsLink": "https://www.example.com/terms",
    "privacyPolicyLink": "https://www.example.com/privacy",
    "optInWorkflow": "Users opt in by creating an account on...",
    "optInMessage": "Example Corp: You have opted in...",
    "helpMessage": "Example Corp: For help call...",
    "stopMessage": "You are unsubscribed from...",
    "numberCapabilities": "SMS",
    "messageType": "Transactional",
    "useCase": "TWO_FACTOR_AUTHENTICATION",
    "subscriberOptIn": "Yes",
    "subscriberOptOut": "Yes",
    "subscriberHelp": "Yes",
    "directLending": "No",
    "embeddedLink": "No",
    "embeddedPhone": "No",
    "ageGated": "No",
    "messageSample1": "Your One-Time Password for Example Corp is [OTP Code]..."
  },
  "attachments": {
    "optInScreenshot": "uploads/req-abc123/optInScreenshot.png"
  },
  "phoneConfig": {
    "messageType": "TRANSACTIONAL",
    "capabilities": ["SMS"]
  }
}
```

**Response:**
```json
{
  "requestId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "Registration workflow started"
}
```

### `POST /api/upload-url`

Generate a presigned S3 URL for direct browser-to-S3 file upload.

**Request body:**
```json
{
  "requestId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "fieldName": "optInScreenshot",
  "contentType": "image/png"
}
```

**Response:**
```json
{
  "uploadUrl": "https://s3.amazonaws.com/bucket/uploads/req-abc/optInScreenshot.png?X-Amz-...",
  "s3Key": "uploads/a1b2c3d4-e5f6-7890-abcd-ef1234567890/optInScreenshot.png",
  "bucket": "10dlc-uploads-111122223333",
  "expiresIn": 600
}
```

**Allowed content types:** `image/png`, `image/jpeg`, `application/pdf`
**Max file size:** 500 KB

### `POST /api/resume/{requestId}`

Resume a paused workflow after human intervention on a rejected registration.

**Response (success):**
```json
{
  "message": "Workflow resumed for request a1b2c3d4-...",
  "resumedFrom": "campaign_human_intervention"
}
```

**Response (no pending intervention):**
```json
{
  "error": "No pending human intervention found for this request",
  "currentStatus": "CAMPAIGN_SUBMITTED"
}
```

## Prerequisites

- AWS CLI v2
- AWS SAM CLI
- Python 3.12+
- An AWS account with AWS End User Messaging SMS enabled in the target region

## Deployment

### First-time deployment

```bash
sam build
sam deploy --guided
```

SAM will prompt for:
- **Stack name** — e.g., `10dlc-registration-automation`
- **AWS Region** — must be a region where EUM SMS is available
- **NotificationEmail** — email address for SNS alerts (you'll need to confirm the subscription)
- **AllowedOrigin** — CORS origin for the front end (use `*` for dev, your domain for prod)

### Subsequent deployments

```bash
sam build && sam deploy
```

### After deployment

1. Confirm the SNS email subscription (check your inbox)
2. Note the API Gateway endpoint from the stack outputs
3. Update the front end wizard to point to your API endpoint
4. Host the front end (S3 static website, CloudFront, or locally)

## Configuration

### SAM Template Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `NotificationEmail` | (required) | Email for registration status alerts |
| `AllowedOrigin` | `*` | CORS allowed origin for the front end |

### Environment Variables (set automatically by SAM)

| Variable | Used By | Description |
|----------|---------|-------------|
| `REGISTRATIONS_TABLE` | All Lambdas | DynamoDB table name |
| `UPLOAD_BUCKET` | Presigned URL, Campaign | S3 bucket name |
| `STATE_MACHINE_ARN` | Intake | Step Functions ARN |
| `NOTIFICATION_TOPIC_ARN` | Notification | SNS topic ARN |

## Infrastructure Resources

| Resource | Type | Purpose |
|----------|------|---------|
| DynamoDB Table | `PAY_PER_REQUEST` | Registration state, form data, task tokens |
| S3 Bucket | Private, encrypted, 90-day lifecycle | File upload staging |
| SNS Topic | Email subscription | Operator notifications |
| API Gateway | HTTP API with CORS | Front end → Lambda |
| EventBridge Rule | `source: aws.sms-voice` | Registration status change routing |
| Step Functions | Standard Workflow | Multi-week registration orchestration |
| 9 Lambda Functions | Python 3.12 | Business logic |

## Costs

- **Step Functions:** Standard Workflows charge per state transition, but idle wait states (waiting for EventBridge callbacks) are free. A typical registration uses ~20-30 transitions.
- **DynamoDB:** Pay-per-request billing — minimal cost for registration volumes.
- **S3:** Negligible — small files with 90-day auto-deletion.
- **Lambda:** Minimal — each function runs for seconds, invoked a handful of times per registration.
- **EventBridge:** First 14M events/month are free.
- **EUM SMS:** Registration fees apply (brand registration fee, $40 vetting fee, monthly campaign fee, monthly phone number lease). See [AWS End User Messaging Pricing](https://aws.amazon.com/end-user-messaging/pricing/).

## Security

- S3 bucket blocks all public access; uploads use time-limited presigned URLs
- S3 server-side encryption (AES-256) enabled
- All Lambda functions use least-privilege IAM policies scoped to specific resources
- API Gateway CORS is configurable via the `AllowedOrigin` parameter
- No AWS credentials are exposed to the front end
- DynamoDB encryption at rest enabled by default

## Additional Resources

- [10DLC Registration Best Practices](https://aws.amazon.com/blogs/messaging-and-targeting/10dlc-registration-best-practices-to-send-sms-with-amazon-pinpoint/)
- [How to Build a Compliant SMS Opt-In Process](https://aws.amazon.com/blogs/messaging-and-targeting/how-to-build-a-compliant-sms-opt-in-process-with-amazon-pinpoint/)
- [Monitoring EUM SMS Registrations with Lambda](https://aws.amazon.com/blogs/messaging-and-targeting/monitoring-aws-end-user-messaging-sms-registrations-with-lambda/)
- [AWS End User Messaging SMS User Guide — Registrations](https://docs.aws.amazon.com/sms-voice/latest/userguide/registrations.html)
- [AWS End User Messaging Pricing](https://aws.amazon.com/end-user-messaging/pricing/)
- [CLI Reference: pinpoint-sms-voice-v2](https://docs.aws.amazon.com/cli/latest/reference/pinpoint-sms-voice-v2/)
