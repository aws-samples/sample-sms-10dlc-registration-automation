<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# ADR-008: Use Second-Person Pronouns in Security Documentation

**Status:** Accepted
**Date:** 2026-04-22
**Deciders:** Project team
**Finding Severity:** Medium (scanner classification)
**Source:** Security review

## Context

Security review flagged the use of second-person pronouns ("you", "your") in
security documentation, recommending third-person or imperative language instead.

The finding appeared in the README security section, security design document,
and user guide FAQ.

## Decision

Keep second-person pronouns in customer-facing documentation. This is a deliberate
style choice aligned with AWS documentation conventions.

AWS documentation and sample code READMEs consistently use second-person pronouns
when addressing the reader directly about their responsibilities. Examples from
official AWS documentation:

- "You are responsible for securing your workload" (AWS Shared Responsibility Model)
- "You can use IAM policies to control access" (IAM User Guide)
- "Before you begin, make sure you have the following" (standard prerequisites format)

Second-person pronouns make security responsibilities clearer and more direct than
third-person alternatives. "You must restrict CORS origins" is more actionable than
"The deployer should restrict CORS origins."

## Consequences

### Risk Accepted
- Scanner flags second-person pronouns as non-clinical language.
- This finding recurs on each scan.

### Mitigations in Place
- Documentation follows AWS style guide conventions for customer-facing content.
- Security responsibilities are clearly stated with specific actions.
- The production security hardening guide provides step-by-step commands.

### Review Trigger
- Re-evaluate if AWS documentation style guide changes to prohibit second-person
  pronouns in security contexts.

## Alternatives Considered

### Option 1: Rewrite all security docs in third person
- **Effort:** Medium
- **Why rejected:** Makes the documentation less direct and harder to follow.
  "The operator should review IAM policies" is less clear than "Review IAM
  policies for your environment."

## References
- [AWS Documentation Style Guide](https://docs.aws.amazon.com/awsstyleguide/latest/styleguide/)
- [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/)
