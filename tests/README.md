<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# Testing the 10DLC Registration Automation

## Prerequisites

Before running any tests, verify you have the following installed and configured:

- **Python 3.12+** - [Download](https://www.python.org/downloads/)
- **AWS CLI v2** - [Install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **AWS SAM CLI** - [Install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- **pytest** - installed via `pip install -r tests/requirements.txt`
- **boto3 and moto** - installed via `pip install -r tests/requirements.txt`
- **requests** - installed via `pip install requests` (for integration tests)
- **AWS credentials** configured with permissions for AWS Step Functions, Amazon DynamoDB, Amazon S3, Amazon SNS, and AWS End User Messaging SMS
- A **deployed stack** (for Layer 3+ tests) - see Deployment section in the main README

## The Problem

The full 10DLC registration workflow takes 6-8 weeks end-to-end because each step
(brand approval, vetting, campaign approval) requires real third-party review.
You cannot run a quick integration test against the live pipeline.

## Solution: Layered Testing Strategy

### Layer 1: Unit Tests
Validate each Lambda function's logic in isolation with mocked boto3 calls.

```bash
cd tests/unit
pip install -r requirements.txt
pytest -v
```

### Layer 2: SAM Local Invoke
Test Lambda handlers locally with realistic event payloads.

```bash
cd 10dlc-registration-automation
sam build
sam local invoke IntakeFunction --event tests/events/intake-submit.json
sam local invoke EventRouterFunction --event tests/events/eventbridge-brand-complete.json
```

### Layer 3: Synthetic Integration Test (the big one)

Deploy the stack, submit a real registration, then **simulate** Amazon EventBridge callbacks
to drive the entire AWS Step Functions workflow through all states in minutes instead of weeks.

```bash
# Deploy first
sam build && sam deploy --guided

# Run the synthetic test - drives the full happy path
python tests/integration/test_orchestrator.py \
    --stack-name 10dlc-registration-automation \
    --scenario happy-path

# Test rejection + human intervention path
python tests/integration/test_orchestrator.py \
    --stack-name 10dlc-registration-automation \
    --scenario brand-rejected

# Test all scenarios
python tests/integration/test_orchestrator.py \
    --stack-name 10dlc-registration-automation \
    --scenario all
```

### Layer 4: Real End-to-End
One actual registration to validate real Amazon EventBridge events flow correctly.
Only needed once to confirm the event schema matches the synthetic events.

---

## Test Scenarios

| Scenario | Path | What It Tests |
|----------|------|---------------|
| `happy-path` | Brand approved > Campaign approved > Phone > Done | Normal flow, no vetting |
| `happy-path-with-vetting` | Brand approved > Vetting approved > Campaign approved > Phone > Done | Full flow with vetting |
| `brand-rejected` | Brand rejected > Notify > Human fix > Campaign approved > Done | Brand rejection + resume |
| `campaign-rejected` | Brand approved > Campaign rejected > Notify > Human fix > Phone > Done | Campaign rejection + resume |
| `vetting-failed` | Brand approved > Vetting failed > Notify > Human decision > Campaign approved > Phone > Done | Vetting failure with human decision to proceed |
| `all` | Runs all scenarios sequentially | Full coverage |

## How the Synthetic Test Works

The test orchestrator:

1. **Submits** a registration via the Amazon API Gateway `/api/submit` endpoint
2. **Polls** the AWS Step Functions execution until it reaches a `waitForTaskToken` state
3. **Reads** the task token from Amazon DynamoDB
4. **Calls** `SendTaskSuccess` or `SendTaskFailure` directly on the task token (simulating the Amazon EventBridge callback)
5. **Repeats** for each wait state in the workflow
6. **Validates** the final Amazon DynamoDB state matches expectations

This bypasses the real third-party review process while exercising the exact same
code paths that production traffic uses.

## File Structure

```
tests/
├── README.md                          # This file
├── requirements.txt                   # Test dependencies
├── unit/                              # Unit tests (mocked)
│   ├── conftest.py                    # Shared fixtures
│   ├── test_intake.py
│   ├── test_event_router.py
│   ├── test_notification.py
│   ├── test_presigned_url.py
│   └── test_resume.py
├── integration/                       # Synthetic integration tests
│   ├── test_orchestrator.py           # Main test runner
│   ├── event_simulator.py            # Simulates EventBridge callbacks via task tokens
│   ├── helpers.py                     # Shared utilities
│   └── check_item.py                 # Quick DynamoDB item inspector
└── events/                            # SAM local invoke event fixtures
    ├── intake-submit.json
    ├── eventbridge-brand-complete.json
    ├── eventbridge-brand-rejected.json
    ├── eventbridge-campaign-complete.json
    ├── eventbridge-campaign-rejected.json
    ├── eventbridge-vetting-complete.json
    ├── eventbridge-vetting-failed.json
    ├── presigned-url-request.json
    └── resume-request.json
```

## Conclusion

The layered testing strategy validates the full 10DLC registration workflow without waiting weeks for real carrier approvals. Unit tests catch logic errors fast, SAM local invoke validates handler behavior with realistic payloads, and the synthetic integration tests drive the entire AWS Step Functions state machine through every path (happy path, rejections, human intervention, and vetting failures) in minutes.

For day-to-day development, run unit tests after every code change and the synthetic integration suite after deploying. Reserve real end-to-end testing for initial setup validation and major architectural changes.
