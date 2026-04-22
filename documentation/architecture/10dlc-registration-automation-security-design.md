<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# 10DLC Registration Automation - Security Design

## Shared Responsibility Model

This solution operates under the [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/).

**AWS is responsible for:**
- Security of the underlying cloud infrastructure (compute, storage, networking, managed services)
- Physical security of data centers
- Managed service security (Amazon DynamoDB encryption, AWS Lambda execution environment isolation, Amazon API Gateway TLS termination)

**You (the customer) are responsible for:**
- Reviewing and configuring IAM policies appropriate for your environment
- Restricting CORS origins from `*` to your specific domain before production use
- Enabling AWS CloudTrail for API audit logging
- Configuring Amazon CloudWatch alarms for error monitoring
- Implementing authentication on Amazon API Gateway (Amazon Cognito, Lambda authorizer, or IAM)
- Reviewing data handling practices for compliance with your organization's requirements
- Managing access to the AWS account where this solution is deployed
- Performing your own security assessment before production deployment

This sample code is provided as-is for demonstration purposes. You are responsible for making your own independent assessment and implementing appropriate security controls for your use case.

## Overview

This document describes the security architecture and controls for the 10DLC Registration Automation solution.

## Data Classification

| Data Type | Classification | Storage | Encryption |
|-----------|---------------|---------|------------|
| Company name, address, contact info | Business-sensitive | Amazon DynamoDB | AWS managed encryption at rest |
| Tax ID (EIN) | Sensitive PII | Amazon DynamoDB | AWS managed encryption at rest |
| Opt-in screenshots, T&C, privacy policy | Business documents | Amazon S3 | AES-256 server-side encryption |
| AWS Step Functions task tokens | System internal | Amazon DynamoDB | AWS managed encryption at rest |
| Registration IDs | System internal | Amazon DynamoDB | AWS managed encryption at rest |
| Phone numbers (E.164) | PII | Amazon DynamoDB | AWS managed encryption at rest |
| Amazon SNS notification content | Business-sensitive | In transit only | TLS in transit |

## Data Flow

```
Browser --> (HTTPS) --> Amazon API Gateway --> (IAM role) --> AWS Lambda --> (IAM role) --> Amazon DynamoDB
                                                                       --> (IAM role) --> Amazon S3 (presigned URL)
                                                                       --> (IAM role) --> AWS Step Functions
                                                                       --> (IAM role) --> AWS End User Messaging SMS API
                                                                       --> (IAM role) --> Amazon SNS

Amazon EventBridge --> (IAM role) --> Event Router Lambda --> (IAM role) --> Amazon DynamoDB
                                                          --> (IAM role) --> AWS Step Functions
```

All data in transit uses TLS. No data flows over unencrypted channels.

## Encryption Strategy

### At Rest
- **Amazon DynamoDB:** AWS managed encryption with SSE enabled explicitly in the CloudFormation template. Point-in-time recovery is enabled.
- **Amazon S3:** AES-256 server-side encryption (SSE-S3). Upload bucket enforces encryption on all objects.
- **Amazon S3 access logs:** AES-256 server-side encryption in dedicated logging bucket.

### In Transit
- **Amazon API Gateway:** HTTPS only (TLS 1.2+)
- **Amazon S3 presigned URLs:** HTTPS only. Bucket policy denies `s3:*` when `aws:SecureTransport` is `false`.
- **AWS Lambda to AWS services:** All AWS SDK calls use HTTPS by default.
- **Amazon SNS notifications:** Email delivery uses TLS where the recipient's mail server supports it.

### Key Management
This solution uses AWS managed encryption keys (SSE-S3 for Amazon S3, AWS owned keys for Amazon DynamoDB). Customer managed keys (CMK) via AWS KMS are not used because:
1. The data does not require customer-controlled key rotation or cross-account access
2. AWS managed keys provide sufficient protection for business-sensitive (non-regulated) data
3. Using CMKs would add operational complexity and cost without meaningful security benefit for this use case

If your use case involves regulated data (HIPAA, PCI, etc.), replace SSE-S3 with SSE-KMS and configure a customer managed key.

## IAM Design

### Principle: Per-Function Roles with Scoped Actions

Each AWS Lambda function has its own IAM execution role with only the actions it needs.

| Function | Amazon DynamoDB | Amazon S3 | AWS End User Messaging SMS | AWS Step Functions | Amazon SNS |
|----------|----------|-----|---------|---------------|-----|
| Intake | Read/Write | - | - | StartExecution | - |
| Presigned URL | - | PutObject | - | - | - |
| Brand Registration | Read/Write | - | Create, Put, Submit | - | - |
| Vetting | Read/Write | - | Create, Associate, Submit | - | - |
| Campaign Registration | Read/Write | Read | Create, Associate, Put, Submit, Attach | - | - |
| Phone Number | Read/Write | - | Request, Associate | - | - |
| Event Router | Read/Write | - | - | SendTaskSuccess/Failure | - |
| Notification | Read | - | Describe | - | Publish |
| Resume | Read/Write | - | - | SendTaskSuccess | - |

### Resource Scoping

- **Amazon DynamoDB, Amazon S3, Amazon SNS, AWS Step Functions:** All scoped to specific resource ARNs using SAM policy templates.
- **AWS End User Messaging SMS actions:** Some actions (`CreateRegistration`, `CreateRegistrationAttachment`, `TagResource`, `RequestPhoneNumber`) do not support resource-level permissions per the [AWS Service Authorization Reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_awsendusermessagingsmsandvoicev2.html) and require `Resource: '*'`. See [ADR-001](decision-records/adr-001-iam-resource-wildcards.md) for the full analysis.

## Amazon S3 Security Controls

| Control | Status |
|---------|--------|
| Block Public Access | Enabled (all four settings) on both buckets |
| Server-side encryption | AES-256 (SSE-S3) on both buckets |
| TLS enforcement | Bucket policy denies non-HTTPS requests on both buckets |
| Versioning | Enabled on upload bucket |
| Access logging | Enabled (logs to dedicated bucket with 365-day retention) |
| Lifecycle rules | Objects expire after 90 days, old versions after 30 days |
| CORS | Configurable via `AllowedOrigin` parameter - you must restrict this in production |
| Presigned URL expiry | 10 minutes |
| File validation | PNG, JPEG, PDF only; 500 KB maximum |

## Amazon API Gateway Security

- **Authentication:** HTTP API with open access for the wizard front end. You must add authentication (Amazon Cognito, Lambda authorizer, or IAM) before production use.
- **CORS:** Configurable via the `AllowedOrigin` SAM parameter. You must restrict this to your specific domain in production.
- **Input validation:** Lambda functions validate request bodies and reject malformed input.
- **Rate limiting:** API Gateway default throttling applies. You should add usage plans for production.

## Monitoring and Logging

| Service | Logging | Your Responsibility |
|---------|---------|---------------------|
| AWS Lambda | Amazon CloudWatch Logs (automatic) | Review logs for errors |
| Amazon API Gateway | Amazon CloudWatch Logs | You must enable access logging for production |
| Amazon S3 | Server access logs to dedicated bucket | Enabled by this solution |
| AWS Step Functions | Amazon CloudWatch Logs | You must enable execution logging for production |
| Amazon DynamoDB | AWS CloudTrail data events | You must enable for production audit logging |

## Customer Responsibilities Before Production Use

The following are your responsibilities under the shared responsibility model. These are not optional recommendations - they are required for production security:

| Priority | Action | Why |
|----------|--------|-----|
| 1 | Restrict `AllowedOrigin` to your domain | Prevents cross-origin attacks from unauthorized domains |
| 2 | Add authentication to Amazon API Gateway | Prevents unauthorized access to registration endpoints |
| 3 | Enable AWS CloudTrail | Provides audit trail for all API calls across services |
| 4 | Enable Amazon CloudWatch alarms | Alerts on Lambda errors, AWS Step Functions failures, Amazon DynamoDB throttling |
| 5 | Enable AWS X-Ray tracing | Provides end-to-end request tracing for debugging |
| 6 | Consider AWS WAF | Rate limiting and IP filtering for Amazon API Gateway |
| 7 | Consider AWS KMS | Replace SSE-S3 with SSE-KMS if handling regulated data |
