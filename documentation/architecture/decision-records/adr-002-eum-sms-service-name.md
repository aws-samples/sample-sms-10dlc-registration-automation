<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# ADR-002: False Positive - "AWS End User Messaging SMS" Service Name

**Status:** Accepted
**Date:** 2026-04-20
**Deciders:** Project team
**Finding Severity:** High (scanner classification)
**Source:** Security review

## Context

Security review flagged "AWS End User Messaging SMS" as an invented or fictitious
service name. The scanner's service registry did not recognize this name and flagged
it in the frontend HTML files.

The finding appeared in `frontend/10dlc-registration-wizard.html` and
`frontend/toll-free-registration-wizard.html`.

## Decision

No change required. This is a false positive. "AWS End User Messaging SMS" is the
official name of the AWS service formerly known as Amazon Pinpoint SMS. The service
was rebranded in 2024.

Evidence:
- The AWS End User Messaging SMS User Guide uses this name throughout.
- The AWS End User Messaging pricing page uses this name.
- The Service Authorization Reference lists it as "AWS End User Messaging SMS and
  Voice V2".
- The CLI namespace remains `pinpoint-sms-voice-v2` (legacy naming), but the service
  name is "AWS End User Messaging SMS".

The scanner's service name registry has not been updated to include this rebranded
service.

## Consequences

### Risk Accepted
- None. The service name is correct per current AWS documentation and branding.

### Mitigations in Place
- This ADR documents the false positive for future scan reviewers.
- If the scanner is updated to recognize the service name, this finding will no longer
  appear.

### Review Trigger
- Remove this ADR if the scanning tool updates its service registry to include
  "AWS End User Messaging SMS".

## Alternatives Considered

### Option 1: Use the old name "Amazon Pinpoint SMS"
- **Effort:** Low
- **Why rejected:** The old name is deprecated. Using it would be incorrect per current
  AWS branding guidelines and could trigger a different scanner finding for using a
  deprecated service name.

## References
- [AWS End User Messaging SMS User Guide](https://docs.aws.amazon.com/sms-voice/latest/userguide/what-is-service.html)
- [AWS End User Messaging Pricing](https://aws.amazon.com/end-user-messaging/pricing/)
- [Service Authorization Reference - End User Messaging SMS V2](https://docs.aws.amazon.com/service-authorization/latest/reference/list_awsendusermessagingsmsandvoicev2.html)
