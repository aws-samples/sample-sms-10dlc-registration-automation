<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# 10DLC Registration Automation - Architecture Diagram Description

Use this description to create or update the system architecture diagram in draw.io. Use official AWS Architecture Icons (2024+).

---

## Diagram Layout

The diagram has 4 horizontal swim lanes flowing left to right:

1. **Client Layer** (left)
2. **API Layer** (center-left)
3. **Orchestration Layer** (center)
4. **AWS Services Layer** (right)

Plus a **Callback Loop** that flows from right back to center.

---

## Components and Connections

### Client Layer

**Component: Registration Wizard (Static HTML)**
- Icon: User / Browser
- Label: "Registration Wizard (Static HTML)"
- Two outbound arrows:
  1. Arrow to Amazon API Gateway labeled "POST /api/submit (form data)"
  2. Arrow to Amazon S3 labeled "PUT (presigned URL upload)"

---

### API Layer

**Component: Amazon API Gateway (HTTP API)**
- Icon: Amazon API Gateway
- Label: "Amazon API Gateway (HTTP API)"
- Three outbound arrows to Lambda functions:
  1. "POST /api/submit" --> Intake Lambda
  2. "POST /api/upload-url" --> Presigned URL Lambda
  3. "POST /api/resume/{id}" --> Resume Lambda

**Component: Intake Lambda**
- Icon: AWS Lambda
- Label: "IntakeFunction"
- Two outbound arrows:
  1. Arrow to Amazon DynamoDB labeled "Write registration data"
  2. Arrow to AWS Step Functions labeled "StartExecution"

**Component: Presigned URL Lambda**
- Icon: AWS Lambda
- Label: "PresignedUrlFunction"
- One outbound arrow:
  1. Arrow to Amazon S3 labeled "Generate presigned PUT URL"

**Component: Resume Lambda**
- Icon: AWS Lambda
- Label: "ResumeFunction"
- Two outbound arrows:
  1. Arrow to Amazon DynamoDB labeled "Read task token"
  2. Arrow to AWS Step Functions labeled "SendTaskSuccess"

---

### Orchestration Layer

**Component: AWS Step Functions (Standard Workflow)**
- Icon: AWS Step Functions
- Label: "Registration Workflow (Standard)"
- This is the central component. Show it as a large box with the internal state flow:

**Internal State Flow (show as a vertical flowchart inside the Step Functions box):**

```
[Start]
   |
   v
[CreateBrandRegistration] --> Brand Registration Lambda
   |
   v
[WaitForBrandApproval] <-- waitForTaskToken (pauses here)
   |
   |--- (on failure) --> [BrandRejected] --> Notification Lambda --> [WaitForHumanIntervention_Brand]
   |                                                                        |
   |                                                                        v (resume)
   v (on success)
[ShouldVetBrand?] -- yes --> [CreateBrandVetting] --> Vetting Lambda
   |                              |
   | no                           v
   |                    [WaitForVettingApproval] <-- waitForTaskToken
   |                         |
   |                         |--- (on failure) --> [VettingFailed] --> Notification Lambda --> [WaitForHumanIntervention_Vetting]
   |                         |                                                                        |
   |                         v (on success)                                                           v (resume)
   |<------------------------+<-----------------------------------------------------------------------+
   |
   v
[CreateCampaignRegistration] --> Campaign Registration Lambda
   |
   v
[WaitForCampaignApproval] <-- waitForTaskToken (pauses here)
   |
   |--- (on failure) --> [CampaignRejected] --> Notification Lambda --> [WaitForHumanIntervention_Campaign]
   |                                                                           |
   |                                                                           v (resume)
   v (on success)
[RequestPhoneNumber] --> Phone Number Lambda
   |
   v
[NotifyComplete] --> Notification Lambda
   |
   v
[RegistrationComplete - Success]
```

**Outbound arrows from Step Functions to Lambda functions:**
1. Arrow to Brand Registration Lambda labeled "create_and_submit"
2. Arrow to Vetting Lambda labeled "create_and_submit"
3. Arrow to Campaign Registration Lambda labeled "create_and_submit"
4. Arrow to Phone Number Lambda labeled "request_and_associate"
5. Arrow to Notification Lambda labeled "notify (brand/campaign/vetting/complete)"

---

### AWS Services Layer (right side)

**Component: Amazon DynamoDB**
- Icon: Amazon DynamoDB
- Label: "Registrations Table"
- Receives arrows from: Intake, Brand Registration, Vetting, Campaign Registration, Phone Number, Event Router, Resume
- Note: "Stores registration state, form data, task tokens"
- Show GSIs: "brand-reg-index, campaign-reg-index"

**Component: Amazon S3**
- Icon: Amazon S3
- Label: "Upload Bucket (encrypted, versioned)"
- Receives arrows from: Browser (presigned URL upload), Campaign Registration Lambda (read attachments)
- Second smaller S3 icon labeled "Access Logs Bucket"

**Component: Amazon SNS**
- Icon: Amazon SNS
- Label: "Notification Topic"
- Receives arrow from: Notification Lambda
- Outbound arrow to: Email icon labeled "Operator Email"

**Component: AWS End User Messaging SMS**
- Icon: Use the generic AWS icon (no specific icon exists yet)
- Label: "AWS End User Messaging SMS"
- Receives arrows from: Brand Registration Lambda, Vetting Lambda, Campaign Registration Lambda, Phone Number Lambda
- Labels on arrows: "CreateRegistration, PutRegistrationFieldValue, SubmitRegistrationVersion, CreateRegistrationAssociation, RequestPhoneNumber"

---

### Callback Loop (the key architectural pattern)

**Component: Amazon EventBridge**
- Icon: Amazon EventBridge
- Label: "EventBridge (Default Bus)"
- Inbound arrow from: AWS End User Messaging SMS labeled "Registration Status Change events"
- Outbound arrow to: Event Router Lambda

**Component: Event Router Lambda**
- Icon: AWS Lambda
- Label: "EventRouterFunction"
- Inbound arrow from: Amazon EventBridge
- Two outbound arrows:
  1. Arrow to Amazon DynamoDB labeled "Lookup task token (via GSI)"
  2. Arrow to AWS Step Functions labeled "SendTaskSuccess / SendTaskFailure"

**Show the callback loop as a distinct colored path:**
```
AWS End User Messaging SMS --> EventBridge --> Event Router Lambda --> DynamoDB (lookup token) --> Step Functions (resume)
```
This loop is what makes the multi-week workflow possible without polling.

---

## Security Annotations

Add these as small callout boxes or annotations:

- On the S3 bucket: "AES-256 encryption, TLS enforced, versioning enabled, Block Public Access"
- On the API Gateway: "HTTPS only, CORS configurable"
- On DynamoDB: "Encryption at rest (SSE), PITR enabled"
- On the presigned URL arrow: "10-min expiry, PNG/JPEG/PDF only, 500KB max"
- On each Lambda: "Per-function IAM role"

---

## Color Coding Suggestion

- **Green arrows:** Happy path (approval flow)
- **Red arrows:** Rejection/failure path
- **Orange arrows:** Human intervention (resume) path
- **Blue arrows:** EventBridge callback loop
- **Gray arrows:** Data storage (DynamoDB, S3)

---

## Diagram Title

"10DLC Registration Automation - System Architecture"

Subtitle: "AWS Step Functions orchestrates multi-week 10DLC registration with event-driven callbacks via Amazon EventBridge"
