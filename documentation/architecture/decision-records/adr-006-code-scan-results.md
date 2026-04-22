<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# ADR-006: Code Scan Results Not Bundled in Repository

**Status:** Accepted
**Date:** 2026-04-21
**Deciders:** Project team
**Finding Severity:** Low
**Source:** Security review

## Context

During the security review process, code scanning tools generated detailed reports
containing findings, rule IDs, and tool-specific metadata. The question arose whether
these scan results should be committed to the repository for traceability.

## Decision

Code scan results are not bundled in the public repository.

Reasons:
1. Scan results contain internal tool names and scanner rule IDs that must not appear
   in public repositories (this project is intended for publication to aws-samples).
2. Scan results are point-in-time artifacts - they reflect the state of the code at
   scan time and become stale as code changes.
3. All findings have been addressed through code fixes and documented in these ADRs.
   The ADRs provide durable documentation of decisions without exposing internal
   tooling details.

## Consequences

### Risk Accepted
- No raw scan output is available in the repository for independent verification.
- Future reviewers cannot see the original scanner output or rule IDs.

### Mitigations in Place
- All findings are documented in ADRs with sufficient context to understand the
  decision without needing the original scan output.
- Code fixes addressing findings are visible in the git history.
- The security design document provides a comprehensive security overview.
- Scan results are retained internally (outside the repository) for audit purposes.

### Review Trigger
- Re-evaluate if a mechanism exists to sanitize scan results of internal tool names
  before publication.
- Re-evaluate if the repository moves to a private hosting model.

## Alternatives Considered

### Option 1: Include redacted scan results
- **Effort:** Medium
- **Why rejected:** Redacting internal tool names and rule IDs from scan output is
  error-prone. Partially redacted reports provide limited value and risk accidental
  disclosure of internal information.

### Option 2: Include scan results in a private branch
- **Effort:** Low
- **Why rejected:** The repository is intended for public publication. Private branches
  add complexity and may be accidentally merged or exposed.

## References
- [AWS Samples Contributing Guidelines](https://github.com/aws-samples/.github/blob/main/CONTRIBUTING.md)
