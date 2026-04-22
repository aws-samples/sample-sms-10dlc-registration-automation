<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# ADR-003: False Positive - "10DLC" Terminology and Spelling

**Status:** Accepted
**Date:** 2026-04-20
**Deciders:** Project team
**Finding Severity:** High (scanner classification)
**Source:** Security review

## Context

Security review flagged "10DLC" as a spelling error, suggesting it should be written
as "10 DLC" with a space. The finding appeared in the HTML wizard title and throughout
the project documentation.

The scanner's style guide rule does not account for industry-specific compound
abbreviations.

## Decision

No change required. This is a false positive. "10DLC" (no space) is the
industry-standard abbreviation for "10-Digit Long Code" as used by The Campaign
Registry (TCR), all US mobile carriers, and AWS itself.

Evidence:
- AWS blog post "10DLC Registration Best Practices" uses "10DLC" throughout.
- AWS End User Messaging SMS User Guide uses "10DLC" in the registrations section.
- The AWS End User Messaging SMS API uses enum values including
  `US_TEN_DLC_BRAND_REGISTRATION`, `US_TEN_DLC_CAMPAIGN_REGISTRATION`, and
  `TEN_DLC`.
- TCR (The Campaign Registry), AT&T, T-Mobile, and Verizon all use "10DLC" as the
  standard abbreviation.

## Consequences

### Risk Accepted
- None. The terminology is correct and matches all authoritative sources.

### Mitigations in Place
- This ADR documents the false positive for future scan reviewers.
- The project consistently uses "10DLC" everywhere (no mixed usage).

### Review Trigger
- Remove this ADR if the scanning tool adds "10DLC" to its approved terminology list.
- Re-evaluate if AWS officially changes the abbreviation format.

## Alternatives Considered

### Option 1: Change to "10 DLC" throughout
- **Effort:** Low
- **Why rejected:** Factually incorrect. No industry source uses "10 DLC" with a space.
  Changing it would confuse readers familiar with the standard terminology and would not
  match the AWS API enum values.

## References
- [AWS 10DLC Registration Best Practices](https://aws.amazon.com/blogs/messaging-and-targeting/10dlc-registration-best-practices-to-send-sms-with-amazon-pinpoint/)
- [AWS End User Messaging SMS User Guide - 10DLC](https://docs.aws.amazon.com/sms-voice/latest/userguide/registrations-10dlc.html)
- [AWS End User Messaging SMS API Reference](https://docs.aws.amazon.com/pinpoint-sms-voice-v2/latest/APIReference/)
