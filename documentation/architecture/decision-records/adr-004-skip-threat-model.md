<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# ADR-004: Skip Formal Threat Model

**Status:** Accepted
**Date:** 2026-04-21
**Deciders:** Project team
**Finding Severity:** Medium
**Source:** Security review

## Context

Security review recommended creating a formal threat model for the solution. A threat
model typically involves structured analysis using frameworks like STRIDE to identify
threats, attack vectors, and trust boundaries.

## Decision

Skip the formal threat model. A security design document has been created instead,
covering:

- Data classification and handling
- Encryption at rest and in transit
- IAM roles and least-privilege policies
- S3 bucket security controls
- API security (API Gateway, presigned URLs)
- Monitoring and logging

This is a sample/reference architecture intended for demonstration and learning
purposes, not a production service. The solution uses only managed AWS services
(Lambda, Step Functions, DynamoDB, S3, API Gateway, SNS, EventBridge) with
well-understood threat profiles documented by AWS.

## Consequences

### Risk Accepted
- No formal STRIDE or similar structured threat analysis exists for this project.
- Edge-case attack vectors that a formal model might surface are not explicitly
  documented.

### Mitigations in Place
- Security design document covers all major security domains.
- All infrastructure is defined in SAM/CloudFormation (auditable, repeatable).
- Only managed AWS services are used - no custom networking, no EC2 instances, no
  self-managed infrastructure.
- Per-function IAM roles with scoped actions.
- S3 bucket policies block public access.
- DynamoDB encryption enabled by default.

### Review Trigger
- Re-evaluate if this solution is adapted for production use.
- Re-evaluate if custom infrastructure components are added.

## Alternatives Considered

### Option 1: Create a full STRIDE threat model
- **Effort:** High
- **Why rejected:** Disproportionate effort for a sample/reference architecture. The
  security design document covers the same concerns in a more accessible format.

### Option 2: Use AWS Threat Composer tool
- **Effort:** Medium
- **Why rejected:** Adds tooling dependency for a sample project. The security design
  document is self-contained and easier to maintain.

## References
- [Security design document](../10dlc-registration-automation-security-design.md)
- [AWS Well-Architected Framework - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
