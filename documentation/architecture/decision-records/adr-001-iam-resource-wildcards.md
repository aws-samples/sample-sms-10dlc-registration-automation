<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# ADR-001: Accepted Risk - IAM Resource Wildcards for AWS End User Messaging SMS Actions

**Status:** Accepted
**Date:** 2026-04-20
**Deciders:** Project team
**Finding Severity:** High
**Source:** Security review

## Context

Security review identified IAM policies in `template.yaml` using `Resource: '*'` for
AWS End User Messaging SMS (`sms-voice`) actions. Each Lambda function has its own IAM
role, but the resource element uses a wildcard for SMS registration actions.

Per the AWS Service Authorization Reference for AWS End User Messaging SMS and Voice V2,
several actions do not support resource-level permissions (the Resource types column is
empty):

| Action | Resource Types |
|--------|---------------|
| `sms-voice:CreateRegistration` | (empty) |
| `sms-voice:CreateRegistrationAttachment` | (empty) |
| `sms-voice:TagResource` | (empty) |
| `sms-voice:RequestPhoneNumber` | (empty) |

These actions create new resources - the ARN does not exist yet at invocation time, so
resource-level scoping is not possible.

Actions like `PutRegistrationFieldValue` and `SubmitRegistrationVersion` DO support
resource-level permissions, but registration IDs are generated dynamically at runtime.
The IDs are not known at deploy time, making static ARN scoping impractical. A single
workflow creates multiple registrations (brand, vetting, campaign) with different IDs.

## Decision

Accept the use of `Resource: '*'` for AWS End User Messaging SMS registration actions.
The risk is mitigated through action-level scoping and per-function IAM roles.

## Consequences

### Risk Accepted
- Lambda functions can operate on any AWS End User Messaging SMS registration in the
  account, not just registrations created by this workflow.
- If a Lambda is compromised, it could modify other registrations in the same account.

### Mitigations in Place
- Per-function IAM roles - each Lambda gets its own role with only its required actions.
- No action wildcards - every policy lists specific actions (no `Action: '*'`).
- DynamoDB, S3, SNS, and Step Functions policies all use resource-scoped ARNs.
- Lambda functions are not internet-facing (invoked by Step Functions and EventBridge).

### Review Trigger
- Re-evaluate if AWS adds resource-level permission support for `CreateRegistration`
  and `CreateRegistrationAttachment`.
- Re-evaluate if this solution is deployed to a shared or production account.
- Re-evaluate if AWS introduces tag-based access control for registration resources.

## Alternatives Considered

### Option 1: Scope to Registration ARN pattern
- **Effort:** Medium
- **Why rejected:** Using `arn:aws:sms-voice:*:*:registration/*` is equivalent to `*`
  for this resource type - it does not meaningfully reduce scope.

### Option 2: Use tag-based conditions
- **Effort:** Low
- **Why rejected:** AWS End User Messaging SMS supports `aws:RequestTag` and
  `aws:TagKeys` conditions for `CreateRegistration` but not for
  `PutRegistrationFieldValue` or `SubmitRegistrationVersion`. Partial coverage does
  not resolve the finding.

### Option 3: Single shared IAM role for all Lambdas
- **Effort:** Low
- **Why rejected:** Less secure than current design. Currently each Lambda has its own
  role with only its needed actions. Consolidating would give every function access to
  every action.

## References
- [AWS Service Authorization Reference - End User Messaging SMS V2](https://docs.aws.amazon.com/service-authorization/latest/reference/list_awsendusermessagingsmsandvoicev2.html)
- [AWS End User Messaging SMS identity-based policy examples](https://docs.aws.amazon.com/sms-voice/latest/userguide/security_iam_id-based-policy-examples.html)
