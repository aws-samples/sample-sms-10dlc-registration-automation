# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Initial project structure** with SAM template, Lambda functions, Step Functions workflow, and frontend wizard
- **Brand registration** Lambda for registering 10DLC brands via AWS End User Messaging
- **Campaign registration** Lambda for creating 10DLC campaigns
- **Phone number management** Lambda for requesting and associating origination numbers
- **Vetting** Lambda for submitting brand vetting requests
- **Intake** Lambda for processing new registration requests
- **Notification** Lambda for sending status updates via SNS
- **Presigned URL** Lambda for secure S3 file uploads
- **Resume** Lambda for resuming paused registration workflows
- **Event router** Lambda for routing Step Functions events
- **Registration workflow** Step Functions state machine for orchestrating the full 10DLC registration process
- **Frontend wizard** HTML-based registration form for collecting customer information
