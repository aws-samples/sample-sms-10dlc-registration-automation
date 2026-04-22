<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# 10DLC Registration Automation - Production Security Hardening Guide

This guide provides step-by-step instructions for hardening this solution
before production use. Complete these steps in priority order.

## Priority 1: Restrict CORS Origin (Critical)

**Risk:** The default `AllowedOrigin=*` allows any website to call your API.

**Measurable outcome:** API requests are only accepted from your specific domain,
reducing the attack surface from all origins to one.

```bash
# Update the AllowedOrigin parameter to your domain
sam deploy --parameter-overrides \
  "NotificationEmail=your-email@example.com" \
  "AllowedOrigin=https://yourdomain.com" \
  "DryRun=false"
```

**Verification:**
```bash
# This should succeed (your domain)
curl -H "Origin: https://yourdomain.com" \
  -X OPTIONS https://<api-id>.execute-api.<region>.amazonaws.com/prod/api/submit

# This should be rejected (different domain)
curl -H "Origin: https://evil.com" \
  -X OPTIONS https://<api-id>.execute-api.<region>.amazonaws.com/prod/api/submit
```

## Priority 2: Add API Authentication (Critical)

**Risk:** The API endpoints are publicly accessible without authentication.

**Measurable outcome:** Only authenticated users can submit registrations or
resume workflows. Unauthorized requests receive 401/403 responses.

Option A - Amazon Cognito User Pool:
```bash
# Create a Cognito user pool
aws cognito-idp create-user-pool \
  --pool-name 10dlc-registration-users \
  --auto-verified-attributes email \
  --query 'UserPool.Id' --output text

# Create an app client
aws cognito-idp create-user-pool-client \
  --user-pool-id <pool-id> \
  --client-name 10dlc-registration-app \
  --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --query 'UserPoolClient.ClientId' --output text
```

Then add a JWT authorizer to the API Gateway in `template.yaml`:
```yaml
Api:
  Type: AWS::Serverless::HttpApi
  Properties:
    Auth:
      DefaultAuthorizer: CognitoAuthorizer
      Authorizers:
        CognitoAuthorizer:
          AuthorizationScopes:
            - email
          IdentitySource: $request.header.Authorization
          JwtConfiguration:
            issuer: !Sub "https://cognito-idp.${AWS::Region}.amazonaws.com/<pool-id>"
            audience:
              - <client-id>
```

Option B - IAM Authorization:
```yaml
# In template.yaml, change the HttpApi auth:
Api:
  Type: AWS::Serverless::HttpApi
  Properties:
    Auth:
      DefaultAuthorizer: AWS_IAM
```

**Verification:**
```bash
# Without auth token - should return 401
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/prod/api/submit \
  -H "Content-Type: application/json" \
  -d '{}'

# With valid auth token - should return 200 or 400 (validation error)
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/prod/api/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{}'
```

## Priority 3: Enable AWS CloudTrail (High)

**Risk:** No audit trail of API calls to AWS services used by this solution.

**Measurable outcome:** All management and data events are logged, providing
forensic capability for security investigations.

```bash
# Create an S3 bucket for CloudTrail logs
aws s3api create-bucket \
  --bucket <your-stack-name>-cloudtrail-<account-id> \
  --region <region>

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket <your-stack-name>-cloudtrail-<account-id> \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Create the trail
aws cloudtrail create-trail \
  --name <your-stack-name>-trail \
  --s3-bucket-name <your-stack-name>-cloudtrail-<account-id> \
  --is-multi-region-trail \
  --enable-log-file-validation

# Start logging
aws cloudtrail start-logging --name <your-stack-name>-trail

# Enable DynamoDB data events (optional - adds cost per event)
aws cloudtrail put-event-selectors \
  --trail-name <your-stack-name>-trail \
  --advanced-event-selectors '[{
    "Name": "DynamoDB data events",
    "FieldSelectors": [
      {"Field": "eventCategory", "Equals": ["Data"]},
      {"Field": "resources.type", "Equals": ["AWS::DynamoDB::Table"]},
      {"Field": "resources.ARN", "StartsWith": ["arn:aws:dynamodb:<region>:<account-id>:table/<your-stack-name>-registrations"]}
    ]
  }]'
```

**Verification:**
```bash
# Check trail status
aws cloudtrail get-trail-status --name <your-stack-name>-trail

# Look for recent events (after a few minutes)
aws cloudtrail lookup-events --max-results 5
```

## Priority 4: Configure Amazon CloudWatch Alarms (High)

**Risk:** Lambda errors, Step Functions failures, and DynamoDB throttling
go unnoticed without alarms.

**Measurable outcome:** Operators are alerted within 5 minutes of any
Lambda error, Step Functions failure, or DynamoDB throttle event.

```bash
# Alarm for Lambda errors (repeat for each function)
aws cloudwatch put-metric-alarm \
  --alarm-name "<stack-name>-IntakeFunction-Errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --dimensions Name=FunctionName,Value=<IntakeFunction-name> \
  --alarm-actions <sns-topic-arn>

# Alarm for Step Functions failures
aws cloudwatch put-metric-alarm \
  --alarm-name "<stack-name>-Workflow-Failures" \
  --metric-name ExecutionsFailed \
  --namespace AWS/States \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --dimensions Name=StateMachineArn,Value=<state-machine-arn> \
  --alarm-actions <sns-topic-arn>

# Alarm for DynamoDB throttling
aws cloudwatch put-metric-alarm \
  --alarm-name "<stack-name>-DynamoDB-Throttles" \
  --metric-name ThrottledRequests \
  --namespace AWS/DynamoDB \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --dimensions Name=TableName,Value=<stack-name>-registrations \
  --alarm-actions <sns-topic-arn>
```

**Verification:**
```bash
aws cloudwatch describe-alarms --alarm-name-prefix "<stack-name>" \
  --query 'MetricAlarms[*].[AlarmName,StateValue]' --output table
```

## Priority 5: Consider AWS WAF (Medium)

**Risk:** No rate limiting or IP filtering on the API Gateway endpoints.

**Measurable outcome:** API requests are rate-limited and known malicious
IPs are blocked before reaching Lambda functions.

```bash
# Create a WAF web ACL with rate limiting
aws wafv2 create-web-acl \
  --name <stack-name>-waf \
  --scope REGIONAL \
  --default-action '{"Allow":{}}' \
  --rules '[{
    "Name": "RateLimit",
    "Priority": 1,
    "Action": {"Block": {}},
    "Statement": {
      "RateBasedStatement": {
        "Limit": 100,
        "AggregateKeyType": "IP"
      }
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "RateLimit"
    }
  }]' \
  --visibility-config '{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"WebACL"}'

# Associate with API Gateway (requires the API Gateway stage ARN)
aws wafv2 associate-web-acl \
  --web-acl-arn <web-acl-arn> \
  --resource-arn "arn:aws:apigateway:<region>::/restapis/<api-id>/stages/prod"
```

## Summary

| Priority | Action | Risk Level | Effort |
|----------|--------|------------|--------|
| 1 | Restrict CORS origin | Critical | Low (parameter change) |
| 2 | Add API authentication | Critical | Medium (Cognito or IAM setup) |
| 3 | Enable CloudTrail | High | Medium (trail + bucket setup) |
| 4 | Configure CloudWatch alarms | High | Medium (alarm per resource) |
| 5 | Add AWS WAF | Medium | Medium (WAF + association) |
