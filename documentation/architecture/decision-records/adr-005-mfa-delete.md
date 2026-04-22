<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# ADR-005: Skip MFA Delete on S3 Buckets

**Status:** Accepted
**Date:** 2026-04-21
**Deciders:** Project team
**Finding Severity:** Medium
**Source:** Security review

## Context

Security review recommended enabling MFA Delete on S3 buckets to prevent accidental
or malicious deletion of objects and bucket versioning configuration.

MFA Delete requires multi-factor authentication for:
- Changing the versioning state of a bucket
- Permanently deleting an object version

## Decision

Skip MFA Delete on S3 buckets for this project.

Reasons:
1. MFA Delete cannot be enabled through CloudFormation or SAM templates. It requires
   the AWS CLI or SDK using root account credentials.
2. Enabling MFA Delete requires root account credentials, which are not available in
   standard deployment workflows and should not be used programmatically.
3. The upload bucket has a 90-day lifecycle policy - data is transient by design.
4. Versioning is already enabled on the buckets, providing protection against
   accidental overwrites.

## Consequences

### Risk Accepted
- S3 objects can be permanently deleted without MFA verification.
- Bucket versioning can be suspended without MFA verification.

### Mitigations in Place
- S3 versioning is enabled (protects against accidental overwrites).
- S3 bucket policies block public access.
- Upload bucket has a 90-day lifecycle policy (data is transient).
- IAM policies restrict which principals can perform delete operations.
- Server-side encryption is enabled on all buckets.

### Review Trigger
- Re-evaluate if CloudFormation/SAM adds native support for MFA Delete.
- Re-evaluate if this solution is adapted for production use with long-lived data.

## Alternatives Considered

### Option 1: Enable MFA Delete via post-deployment script
- **Effort:** High
- **Why rejected:** Requires root account credentials in an automation pipeline, which
  is a security anti-pattern. The operational complexity outweighs the benefit for a
  sample project.

### Option 2: Document as a manual post-deployment step
- **Effort:** Low
- **Why rejected:** Adds friction to the deployment process for a sample project.
  Users who need MFA Delete for production use can enable it manually.

## References
- [AWS S3 - Using MFA Delete](https://docs.aws.amazon.com/AmazonS3/latest/userguide/MultiFactorAuthenticationDelete.html)
- [CloudFormation S3 Bucket VersioningConfiguration](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-s3-bucket-versioningconfiguration.html)
