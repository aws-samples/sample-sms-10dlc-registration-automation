<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Dry run mode for all Lambda functions (set DryRun=true SAM parameter)
- Vetting human intervention - vetting failures pause the workflow for operator decision
- Rejection reason lookup - notifications include specific rejection details from the API
- Enriched notification messages with company name, registration IDs, and next steps
- Security design document with shared responsibility model and customer responsibilities
- ADR-001 through ADR-007 documenting all accepted risks and false positives
- Amazon S3 TLS enforcement, versioning, access logging, and dedicated logs bucket
- Amazon DynamoDB explicit SSE and point-in-time recovery
- Input validation and error handling in Intake Lambda
- Prerequisites, cost warnings, and cleanup sections in HTML wizards
- Cleanup section in README with sam delete and manual resource deletion
- SPDX license headers on all source files

### Changed
- Notification messages rewritten with structured formatting and rejection details

### Fixed
- State machine vetting failure catch block missing ResultPath (crashed notification Lambda)
- State machine Task.Token context object reference ($.Task.Token to $$.Task.Token)
- Throughput numbers corrected (AT&T: 0.2 MPS, not 75 msg/min)
- CLI parameter --text-choices corrected to --select-choices in toll-free wizard
- innerHTML usage replaced with DOM methods in HTML wizards

### Security
- Accepted risk: IAM Resource wildcards for actions without resource-level support (ADR-001)
- False positive: "AWS End User Messaging SMS" is the official service name (ADR-002)
- False positive: "10DLC" is the industry-standard abbreviation (ADR-003)
- Skipped: Formal threat model (ADR-004), MFA Delete (ADR-005)
- Skipped: Code scan results in repo (ADR-006), account-level logging (ADR-007)
