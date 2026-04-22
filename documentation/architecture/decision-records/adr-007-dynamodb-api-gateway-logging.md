<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# ADR-007: DynamoDB CloudTrail Data Events and API Gateway Access Logging Not Enabled

**Status:** Accepted
**Date:** 2026-04-21
**Deciders:** Project team
**Finding Severity:** Medium
**Source:** Security review

## Context

Security review recommended enabling DynamoDB CloudTrail data events and API Gateway
access logging for audit and compliance purposes.

DynamoDB CloudTrail data events would log all GetItem, PutItem, DeleteItem, and other
data-plane operations. API Gateway access logging would log all API requests with
details like caller identity, request time, and response status.

## Decision

DynamoDB CloudTrail data events and API Gateway access logging are not enabled by
default in this stack.

Reasons:
1. CloudTrail data events for DynamoDB are an account-level configuration, not a
   stack-level resource. They are configured in the CloudTrail console or via the
   CloudTrail API, not in individual CloudFormation/SAM templates.
2. CloudTrail data events incur additional cost per event logged. For a sample project,
   this cost should be opt-in rather than imposed by default.
3. API Gateway access logging requires an account-level IAM role
   (`apigateway.amazonaws.com` must be granted CloudWatch Logs permissions at the
   account level). This is a one-time account setup that cannot be reliably managed
   within a single SAM stack.
4. Lambda CloudWatch Logs already provide an audit trail of all function invocations,
   including input events and execution results.

Both items are documented as customer responsibilities in the README and security
design document.

## Consequences

### Risk Accepted
- DynamoDB data-plane operations are not logged to CloudTrail by default.
- API Gateway requests are not logged to CloudWatch Logs access logs by default.
- Forensic analysis of data access patterns requires enabling these features manually.

### Mitigations in Place
- Lambda CloudWatch Logs capture all function invocations with input/output details.
- CloudTrail management events (control-plane operations like CreateTable,
  UpdateTable) are logged by default in all AWS accounts.
- Step Functions execution history provides a complete audit trail of workflow
  execution.
- README and security design document instruct customers to enable these features
  for production use.

### Review Trigger
- Re-evaluate if CloudFormation/SAM adds simplified support for CloudTrail data
  event configuration at the stack level.
- Re-evaluate if this solution is adapted for production use where compliance
  requirements mandate data-plane logging.

## Alternatives Considered

### Option 1: Include CloudTrail trail resource in the SAM template
- **Effort:** Medium
- **Why rejected:** A CloudTrail trail is an account-level resource. Including it in
  the stack could conflict with existing trails and incur unexpected costs. Multiple
  deployments of this stack would create duplicate trails.

### Option 2: Include API Gateway account-level role in the SAM template
- **Effort:** Low
- **Why rejected:** The `AWS::ApiGateway::Account` resource is a singleton per AWS
  account. Including it in the stack could overwrite existing account-level API Gateway
  configurations and break other API Gateway deployments in the same account.

### Option 3: Add a parameter to optionally enable logging
- **Effort:** Medium
- **Why rejected:** Adds template complexity for a sample project. Customers who need
  these features can enable them at the account level following the documentation.

## References
- [CloudTrail data events for DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/logging-using-cloudtrail.html)
- [API Gateway access logging](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html)
- [Security design document](../10dlc-registration-automation-security-design.md)
