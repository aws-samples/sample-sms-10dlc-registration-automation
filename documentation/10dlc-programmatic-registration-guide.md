<!-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 -->

# Programmatic 10DLC Registration Guide

## AWS End User Messaging SMS — CLI Walkthrough

This guide walks through the complete 10DLC registration lifecycle using the AWS CLI (`pinpoint-sms-voice-v2`). The process follows this order:

1. Register your brand (company)
2. Submit the brand registration
3. (Optional but recommended) Create brand vetting, associate the brand, and submit
4. Create a 10DLC campaign registration, associate the brand, populate fields, and submit
5. Request a 10DLC phone number
6. Associate the phone number with the approved campaign

> **Prerequisites**
> - AWS CLI v2 installed and configured
> - IAM permissions for `pinpoint-sms-voice-v2` actions
> - Your company's legal name, EIN/tax ID, physical address, and website
> - An opt-in screenshot or mockup (PNG/JPEG/PDF, max 500 KB)
> - Sample message text for your campaign

> **Important Association Rules (from the API)**
> - Brand vetting requires `ASSOCIATE_BEFORE_SUBMIT` with the brand registration
> - Campaign registration requires `ASSOCIATE_BEFORE_SUBMIT` with the brand registration
> - Phone numbers (TEN_DLC) use `ASSOCIATE_AFTER_COMPLETE` with the campaign — associate after campaign is approved

---

## Step 0: Discover Registration Types and Field Definitions

List all registration types:

```bash
aws pinpoint-sms-voice-v2 describe-registration-type-definitions
```

For 10DLC you'll use:
- `US_TEN_DLC_BRAND_REGISTRATION`
- `US_TEN_DLC_BRAND_VETTING`
- `US_TEN_DLC_CAMPAIGN_REGISTRATION`

Get field definitions for any type:

```bash
aws pinpoint-sms-voice-v2 describe-registration-field-definitions \
    --registration-type US_TEN_DLC_BRAND_REGISTRATION
```

---

## Step 1: Create the Brand Registration

```bash
aws pinpoint-sms-voice-v2 create-registration \
    --registration-type US_TEN_DLC_BRAND_REGISTRATION \
    --tags "Key=Name,Value=MyCompanyBrand"
```

**Save the `RegistrationId`** from the response — you'll need it for every subsequent command.

---

## Step 2: Populate Brand Registration Fields

The brand registration has two sections: `companyInfo` and `contactInfo`.

### Section: companyInfo (all REQUIRED unless noted)

```bash
# Legal company name (must exactly match IRS/tax registration)
# FieldPath: companyInfo.companyName | Type: TEXT | Max: 100 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.companyName \
    --text-value "Example Corp"

# Country of tax registration (2-letter ISO code, uppercase)
# FieldPath: companyInfo.taxIdIssuingCountry | Type: TEXT | Exactly 2 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.taxIdIssuingCountry \
    --text-value "US"

# Tax ID / EIN (9-digit EIN for US, alphanumeric, max 21 chars)
# FieldPath: companyInfo.taxId | Type: TEXT
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.taxId \
    --text-value "123456789"

# Legal form of organization
# FieldPath: companyInfo.legalType | Type: SELECT
# Options: PRIVATE_PROFIT, PUBLIC_PROFIT, NON_PROFIT, GOVERNMENT
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.legalType \
    --text-choices "PRIVATE_PROFIT"

# Stock symbol (CONDITIONAL — required if PUBLIC_PROFIT)
# FieldPath: companyInfo.stockSymbol | Type: TEXT | Max: 10 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.stockSymbol \
    --text-value "EXMPL"

# Stock exchange (CONDITIONAL — required if PUBLIC_PROFIT)
# FieldPath: companyInfo.stockExchange | Type: SELECT
# Options: NONE, NASDAQ, NYSE, AMEX, AMX, ASX, B3, BME, BSE, FRA, ICEX, JPX,
#          JSE, KRX, LON, NSE, OMX, SEHK, SGX, SSE, STO, SWX, SZSE, TSX, TWSE, VSE, OTHER
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.stockExchange \
    --text-choices "NASDAQ"

# Brand verification email (CONDITIONAL — required if PUBLIC_PROFIT)
# FieldPath: companyInfo.businessContactEmail | Type: TEXT | Max: 100 chars
# Email domain must match your business domain. No distribution lists.
# Authentication email comes from noreply@auth.campaignregistry.com
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.businessContactEmail \
    --text-value "janedoe@example.com"

# Physical business address — Street
# FieldPath: companyInfo.address | Type: TEXT | Max: 100 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.address \
    --text-value "123 Main Street"

# Physical business address — City
# FieldPath: companyInfo.city | Type: TEXT | Max: 100 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.city \
    --text-value "Seattle"

# Physical business address — State or region
# FieldPath: companyInfo.state | Type: TEXT | Max: 50 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.state \
    --text-value "WA"

# Physical business address — Zip/Postal Code
# FieldPath: companyInfo.zipCode | Type: TEXT | Max: 20 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.zipCode \
    --text-value "98101"

# Physical business address — Country (2-letter ISO, uppercase)
# FieldPath: companyInfo.isoCountryCode | Type: TEXT | Exactly 2 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path companyInfo.isoCountryCode \
    --text-value "US"
```

### Section: contactInfo (all REQUIRED)

```bash
# DBA or brand name
# FieldPath: contactInfo.dbaName | Type: TEXT | Max: 100 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path contactInfo.dbaName \
    --text-value "Example Corp"

# Vertical (industry category)
# FieldPath: contactInfo.vertical | Type: SELECT
# Options: AGRICULTURE, COMMUNICATION, CONSTRUCTION, EDUCATION, ENERGY,
#          ENTERTAINMENT, FINANCIAL, GAMBLING, GOVERNMENT, HEALTHCARE,
#          HOSPITALITY, INSURANCE, MANUFACTURING, NGO, REAL_ESTATE, RETAIL, TECHNOLOGY
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path contactInfo.vertical \
    --text-choices "TECHNOLOGY"

# Company website (must be publicly accessible)
# FieldPath: contactInfo.website | Type: TEXT | Max: 100 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path contactInfo.website \
    --text-value "https://www.example.com"

# Support email (domain must match website domain)
# FieldPath: contactInfo.supportEmail | Type: TEXT | Max: 100 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path contactInfo.supportEmail \
    --text-value "support@example.com"

# Support phone number (E.164 format)
# FieldPath: contactInfo.supportPhoneNumber | Type: TEXT | Max: 30 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-1234567890abcdef0 \
    --field-path contactInfo.supportPhoneNumber \
    --text-value "+12065550142"
```

---

## Step 3: Submit the Brand Registration

```bash
aws pinpoint-sms-voice-v2 submit-registration-version \
    --registration-id reg-1234567890abcdef0
```

Check status:

```bash
aws pinpoint-sms-voice-v2 describe-registrations \
    --registration-ids reg-1234567890abcdef0
```

- Initial status is `SUBMITTED`, typically moves to `REVIEWING` within 24 hours
- You cannot modify or delete the registration while under review
- If status stays `CREATED` for over 24 hours after submission, open a support case

**Wait for the brand registration to reach `COMPLETED` status before proceeding.**

---

## Step 4: (Optional but Recommended) Brand Vetting

Vetting can increase throughput limits. Without vetting:
- 75 messages/minute to AT&T recipients
- 2,000 messages/day to T-Mobile recipients

There is a **$40 non-refundable fee**. Vetting scores are NOT applied retroactively — vet BEFORE creating campaigns.

> The brand vetting registration type has **no field definitions** — it's just a create, associate, and submit.

```bash
# Create the vetting registration
aws pinpoint-sms-voice-v2 create-registration \
    --registration-type US_TEN_DLC_BRAND_VETTING \
    --tags "Key=Name,Value=MyCompanyVetting"
```

**Save the `RegistrationId`** (e.g., `reg-vetting-id`).

The vetting registration has `ASSOCIATE_BEFORE_SUBMIT` with the brand, so you must associate your approved brand before submitting:

```bash
# Associate the approved brand registration with the vetting registration
aws pinpoint-sms-voice-v2 create-registration-association \
    --registration-id reg-vetting-id \
    --resource-id reg-1234567890abcdef0
```

Then submit:

```bash
aws pinpoint-sms-voice-v2 submit-registration-version \
    --registration-id reg-vetting-id
```

Monitor status:

```bash
aws pinpoint-sms-voice-v2 describe-registrations \
    --registration-ids reg-vetting-id
```

---

## Step 5: Create the Campaign Registration

```bash
aws pinpoint-sms-voice-v2 create-registration \
    --registration-type US_TEN_DLC_CAMPAIGN_REGISTRATION \
    --tags "Key=Name,Value=MyTransactionalCampaign"
```

**Save the `RegistrationId`** (e.g., `reg-campaign-id`).

### Associate the Brand BEFORE Submitting

The campaign has `ASSOCIATE_BEFORE_SUBMIT` with the brand registration, so associate it now:

```bash
aws pinpoint-sms-voice-v2 create-registration-association \
    --registration-id reg-campaign-id \
    --resource-id reg-1234567890abcdef0
```

---

## Step 6: Populate Campaign Registration Fields

The campaign registration has five sections: `campaignInfo`, `campaignCapabilities`, `campaignUseCase`, `messageSamples`, and `mmsFileSamples`.

### Section: campaignInfo

```bash
# Campaign description (min 40 chars, max 4096)
# FieldPath: campaignInfo.campaignName | Type: TEXT | REQUIRED
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignInfo.campaignName \
    --text-value "Example Corp will be sending One Time Password (OTP) messages to our customers who have explicitly opted in to receive these messages for the purpose of authenticating into their account on our application."

# Vertical
# FieldPath: campaignInfo.vertical | Type: SELECT | REQUIRED
# Options: AGRICULTURE, COMMUNICATION, CONSTRUCTION, EDUCATION, ENERGY,
#          ENTERTAINMENT, FINANCIAL, GAMBLING, GOVERNMENT, HEALTHCARE,
#          HOSPITALITY, INSURANCE, MANUFACTURING, NGO, REAL_ESTATE, RETAIL, TECHNOLOGY
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignInfo.vertical \
    --text-choices "TECHNOLOGY"

# Terms & Conditions URL (OPTIONAL — provide URL or file, not both)
# FieldPath: campaignInfo.termsAndConditionsLink | Type: TEXT | Max: 255 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignInfo.termsAndConditionsLink \
    --text-value "https://www.example.com/terms"

# Terms & Conditions file upload (OPTIONAL — alternative to URL)
# FieldPath: campaignInfo.termsAndConditionsFile | Type: ATTACHMENT
# Use create-registration-attachment first, then reference the attachment ID

# Privacy Policy URL (OPTIONAL — provide URL or file, not both)
# FieldPath: campaignInfo.privacyPolicyLink | Type: TEXT | Max: 255 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignInfo.privacyPolicyLink \
    --text-value "https://www.example.com/privacy"

# Privacy Policy file upload (OPTIONAL — alternative to URL)
# FieldPath: campaignInfo.privacyPolicyFile | Type: ATTACHMENT

# Opt-in workflow description (min 40 chars, max 2048) — REQUIRED
# FieldPath: campaignInfo.optInWorkflow | Type: TEXT
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignInfo.optInWorkflow \
    --text-value "Users opt in by creating an account on https://www.example.com and checking the SMS notifications checkbox during registration. The opt-in form includes: program name (Example Corp Alerts), message frequency (1 msg per login), Terms and Conditions link, Privacy Policy link, STOP to cancel instructions, and message and data rates may apply disclosure."

# Opt-in screenshot (OPTIONAL — but required if opt-in is behind login, verbal, or printed)
# FieldPath: campaignInfo.optInScreenshot | Type: ATTACHMENT
# Step 1: Create the attachment
aws pinpoint-sms-voice-v2 create-registration-attachment \
    --attachment-url s3://my-bucket/opt-in-screenshot.png
# Step 2: Associate it (use the RegistrationAttachmentId from above)
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignInfo.optInScreenshot \
    --registration-attachment-id attach-1234567890abcdef0

# Opt-in keyword (OPTIONAL)
# FieldPath: campaignInfo.optInKeyword | Type: TEXT | Max: 255 chars
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignInfo.optInKeyword \
    --text-value "JOIN"

# Opt-in confirmation message — REQUIRED (min 20, max 255 chars)
# FieldPath: campaignInfo.optInMessage | Type: TEXT
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignInfo.optInMessage \
    --text-value "Example Corp: You have opted in to receive OTP messages. Expect one message per login request. Msg & data rates may apply. Reply HELP for help or STOP to cancel."

# HELP message — REQUIRED (min 20, max 255 chars)
# FieldPath: campaignInfo.helpMessage | Type: TEXT
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignInfo.helpMessage \
    --text-value "Example Corp Account Alerts: For help call 1-888-555-0142 or go to example.com. Msg&data rates may apply. Text STOP to cancel."

# STOP message — REQUIRED (min 20, max 255 chars)
# FieldPath: campaignInfo.stopMessage | Type: TEXT
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignInfo.stopMessage \
    --text-value "You are unsubscribed from Example Corp Account Alerts. No more messages will be sent. Text back JOIN or call 1-888-555-0142 to receive messages again."
```

### Section: campaignCapabilities

```bash
# Number capabilities — REQUIRED
# FieldPath: campaignCapabilities.numberCapabilities | Type: SELECT
# Options: "SMS", "SMS and MMS", "SMS and VOICE", "SMS and MMS and VOICE"
# Note: Selecting voice increases review processing time. Cannot be changed later.
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignCapabilities.numberCapabilities \
    --text-choices "SMS"

# Message type (OPTIONAL)
# FieldPath: campaignCapabilities.messageType | Type: SELECT
# Options: "Transactional", "Promotional"
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignCapabilities.messageType \
    --text-choices "Transactional"
```

### Section: campaignUseCase

```bash
# Use case — REQUIRED
# FieldPath: campaignUseCase.useCase | Type: SELECT
# Options: ACCOUNT_NOTIFICATION, CHARITY, CUSTOMER_CARE, DELIVERY_NOTIFICATION,
#          FRAUD_ALERT, HIGHER_EDUCATION, LOW_VOLUME, MARKETING, MIXED,
#          POLLING_VOTING, PUBLIC_SERVICE_ANNOUNCEMENT, SECURITY_ALERT,
#          TWO_FACTOR_AUTHENTICATION
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignUseCase.useCase \
    --text-choices "TWO_FACTOR_AUTHENTICATION"

# Sub use cases (OPTIONAL — REQUIRED if use case is MIXED or LOW_VOLUME)
# FieldPath: campaignUseCase.subUseCases | Type: SELECT | Min 1, Max 5
# Options: ACCOUNT_NOTIFICATION, CUSTOMER_CARE, DELIVERY_NOTIFICATION,
#          FRAUD_ALERT, HIGHER_EDUCATION, MARKETING, POLLING_VOTING,
#          PUBLIC_SERVICE_ANNOUNCEMENT, SECURITY_ALERT, TWO_FACTOR_AUTHENTICATION
# Example for MIXED use case:
# aws pinpoint-sms-voice-v2 put-registration-field-value \
#     --registration-id reg-campaign-id \
#     --field-path campaignUseCase.subUseCases \
#     --text-choices "ACCOUNT_NOTIFICATION" "TWO_FACTOR_AUTHENTICATION"

# Subscriber opt-in — REQUIRED (only option is "Yes")
# FieldPath: campaignUseCase.subscriberOptIn | Type: SELECT
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignUseCase.subscriberOptIn \
    --text-choices "Yes"

# Subscriber opt-out — REQUIRED (only option is "Yes")
# FieldPath: campaignUseCase.subscriberOptOut | Type: SELECT
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignUseCase.subscriberOptOut \
    --text-choices "Yes"

# Subscriber help — REQUIRED (only option is "Yes")
# FieldPath: campaignUseCase.subscriberHelp | Type: SELECT
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignUseCase.subscriberHelp \
    --text-choices "Yes"

# Direct lending or loan arrangement — REQUIRED
# FieldPath: campaignUseCase.directLending | Type: SELECT | Options: "Yes", "No"
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignUseCase.directLending \
    --text-choices "No"

# Embedded link — REQUIRED
# FieldPath: campaignUseCase.embeddedLink | Type: SELECT | Options: "Yes", "No"
# Must align with your message samples. Public URL shorteners (bitly, tinyurl) not accepted.
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignUseCase.embeddedLink \
    --text-choices "No"

# Embedded link sample (OPTIONAL — required if embeddedLink is "Yes")
# FieldPath: campaignUseCase.embeddedLinkSample | Type: TEXT | Max: 255 chars
# aws pinpoint-sms-voice-v2 put-registration-field-value \
#     --registration-id reg-campaign-id \
#     --field-path campaignUseCase.embeddedLinkSample \
#     --text-value "https://www.example.com/verify"

# Embedded phone number — REQUIRED
# FieldPath: campaignUseCase.embeddedPhone | Type: SELECT | Options: "Yes", "No"
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignUseCase.embeddedPhone \
    --text-choices "No"

# Age-gated content — REQUIRED
# FieldPath: campaignUseCase.ageGated | Type: SELECT | Options: "Yes", "No"
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path campaignUseCase.ageGated \
    --text-choices "No"
```

### Section: messageSamples

```bash
# Message sample 1 — REQUIRED (min 20, max 1024 chars)
# FieldPath: messageSamples.messageSample1 | Type: TEXT
# Use realistic messages. Indicate variable fields with brackets like [OTP Code].
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path messageSamples.messageSample1 \
    --text-value "Your One-Time Password for Example Corp is [OTP Code]. Please enter this on the verification screen to complete your account setup."

# Message samples 2-5 are OPTIONAL (same validation: min 20, max 1024 chars)
# FieldPaths: messageSamples.messageSample2 through messageSamples.messageSample5
aws pinpoint-sms-voice-v2 put-registration-field-value \
    --registration-id reg-campaign-id \
    --field-path messageSamples.messageSample2 \
    --text-value "Example Corp: Your login verification code is [OTP Code]. This code expires in 10 minutes. If you did not request this, please ignore."
```

### Section: mmsFileSamples (all OPTIONAL)

Only needed if your campaign uses MMS. Upload attachments first, then reference them.

```bash
# FieldPaths: mmsFileSamples.mmsFileSample1 through mmsFileSamples.mmsFileSample5
# Type: ATTACHMENT | Max 500KB for GIF/JPEG/PNG, 600KB for other types

# aws pinpoint-sms-voice-v2 create-registration-attachment \
#     --attachment-url s3://my-bucket/mms-sample.png
# aws pinpoint-sms-voice-v2 put-registration-field-value \
#     --registration-id reg-campaign-id \
#     --field-path mmsFileSamples.mmsFileSample1 \
#     --registration-attachment-id attach-mms-id
```

---

## Step 7: Submit the Campaign Registration

```bash
aws pinpoint-sms-voice-v2 submit-registration-version \
    --registration-id reg-campaign-id
```

Monitor status:

```bash
aws pinpoint-sms-voice-v2 describe-registrations \
    --registration-ids reg-campaign-id
```

Campaign review takes at least **4-6 weeks** due to manual carrier review. **Wait for the campaign to be approved before proceeding.**

---

## Step 8: Request a 10DLC Phone Number

Once the campaign is approved:

```bash
aws pinpoint-sms-voice-v2 request-phone-number \
    --iso-country-code US \
    --message-type TRANSACTIONAL \
    --number-capabilities SMS \
    --number-type TEN_DLC
```

**Save the `PhoneNumberId`** from the response.

> You are charged the monthly lease fee immediately, regardless of registration status.

---

## Step 9: Associate the Phone Number with the Campaign

The campaign's association behavior for TEN_DLC numbers is `ASSOCIATE_AFTER_COMPLETE`, so you associate after the campaign is approved:

```bash
aws pinpoint-sms-voice-v2 create-registration-association \
    --registration-id reg-campaign-id \
    --resource-id phone-1234567890abcdef0
```

After association, carriers perform an additional review (4-6 weeks).

---

## Step 10: Send a Test Message

Once everything is approved:

```bash
aws pinpoint-sms-voice-v2 send-text-message \
    --destination-phone-number "+15551234567" \
    --origination-identity "+1XXXXXXXXXX" \
    --message-body "Your verification code is 839274. This code expires in 10 minutes." \
    --message-type TRANSACTIONAL
```

---

## Automated Status Monitoring with Amazon EventBridge

Instead of polling `describe-registrations`, you can use Amazon EventBridge to receive real-time notifications when a registration status changes. AWS End User Messaging SMS sends `Registration Status Change` events to EventBridge for the following statuses:

`CREATED`, `SUBMITTED`, `REVIEWING`, `COMPLETE`, `REQUIRES_UPDATES`, `REQUIRES_AUTHENTICATION`, `PROVISIONING`, `CLOSED`, `DELETED`

### Example EventBridge Event

```json
{
    "version": "0",
    "id": "d2e8812b-d34c-90f9-a8a9-3f18e15d1db9",
    "detail-type": "Registration Status Change",
    "source": "aws.sms-voice",
    "account": "111122223333",
    "time": "2025-09-26T17:42:25Z",
    "region": "us-east-1",
    "resources": ["arn:aws:sms-voice:us-east-1:111122223333:registration/registration-30a16a8b7cec478a8e37febbb9005348"],
    "detail": {
        "registrationDetails": {
            "registrationId": "registration-30a16a8b7cec478a8e37febbb9005348",
            "registrationVersionNumber": 1,
            "registrationType": "US_TEN_DLC_CAMPAIGN_REGISTRATION",
            "registrationStatusChangeTimestamp": 1758908543000,
            "currentStatus": "SUBMITTED"
        },
        "registrationArn": "arn:aws:sms-voice:us-east-1:111122223333:registration/registration-30a16a8b7cec478a8e37febbb9005348"
    }
}
```

### Create an EventBridge Rule for Registration Status Changes

```bash
# Create a rule that matches all registration status change events
aws events put-rule \
    --name "10dlc-registration-status-changes" \
    --event-pattern '{
        "source": ["aws.sms-voice"],
        "detail-type": ["Registration Status Change"]
    }' \
    --description "Captures all EUM SMS registration status changes"
```

You can narrow the pattern to specific statuses (e.g., only alert on `REQUIRES_UPDATES` or `COMPLETE`):

```bash
aws events put-rule \
    --name "10dlc-registration-actionable-status" \
    --event-pattern '{
        "source": ["aws.sms-voice"],
        "detail-type": ["Registration Status Change"],
        "detail": {
            "registrationDetails": {
                "currentStatus": ["COMPLETE", "REQUIRES_UPDATES", "REQUIRES_AUTHENTICATION"]
            }
        }
    }' \
    --description "Alert on registration statuses that require action"
```

### Example: Send Notifications to SNS

```bash
# Add an SNS topic as the target for the rule
aws events put-targets \
    --rule "10dlc-registration-status-changes" \
    --targets "Id=sns-target,Arn=arn:aws:sns:us-east-1:111122223333:registration-alerts"
```

### Example: Trigger a Lambda Function

```bash
aws events put-targets \
    --rule "10dlc-registration-status-changes" \
    --targets "Id=lambda-target,Arn=arn:aws:lambda:us-east-1:111122223333:function:process-registration-status"
```

> For a full walkthrough of building an automated registration monitoring solution with Lambda and SES, see [Monitoring AWS End User Messaging SMS Registrations with Lambda](https://aws.amazon.com/blogs/messaging-and-targeting/monitoring-aws-end-user-messaging-sms-registrations-with-lambda/).

---

## Quick Reference: Status Monitoring Commands

```bash
# Check a specific registration
aws pinpoint-sms-voice-v2 describe-registrations \
    --registration-ids reg-1234567890abcdef0

# List all registrations
aws pinpoint-sms-voice-v2 describe-registrations

# Check field values already set
aws pinpoint-sms-voice-v2 describe-registration-field-values \
    --registration-id reg-1234567890abcdef0

# Check registration versions
aws pinpoint-sms-voice-v2 describe-registration-versions \
    --registration-id reg-1234567890abcdef0

# List associations for a registration
aws pinpoint-sms-voice-v2 list-registration-associations \
    --registration-id reg-1234567890abcdef0
```

---

## Complete Field Path Reference

### US_TEN_DLC_BRAND_REGISTRATION

| FieldPath | Title | Type | Requirement |
|-----------|-------|------|-------------|
| `companyInfo.companyName` | Legal company name | TEXT (max 100) | REQUIRED |
| `companyInfo.taxIdIssuingCountry` | Country of tax registration | TEXT (exactly 2) | REQUIRED |
| `companyInfo.taxId` | Tax ID or Business Registration Number | TEXT (max 21) | REQUIRED |
| `companyInfo.legalType` | Legal form of organization | SELECT | REQUIRED |
| `companyInfo.stockSymbol` | Stock symbol | TEXT (max 10) | CONDITIONAL (PUBLIC_PROFIT) |
| `companyInfo.stockExchange` | Stock exchange | SELECT | CONDITIONAL (PUBLIC_PROFIT) |
| `companyInfo.businessContactEmail` | Brand verification email | TEXT (max 100) | CONDITIONAL (PUBLIC_PROFIT) |
| `companyInfo.address` | Street address | TEXT (max 100) | REQUIRED |
| `companyInfo.city` | City | TEXT (max 100) | REQUIRED |
| `companyInfo.state` | State or region | TEXT (max 50) | REQUIRED |
| `companyInfo.zipCode` | Zip/Postal code | TEXT (max 20) | REQUIRED |
| `companyInfo.isoCountryCode` | Country | TEXT (exactly 2) | REQUIRED |
| `contactInfo.dbaName` | DBA or brand name | TEXT (max 100) | REQUIRED |
| `contactInfo.vertical` | Vertical | SELECT | REQUIRED |
| `contactInfo.website` | Company website | TEXT (max 100) | REQUIRED |
| `contactInfo.supportEmail` | Support email | TEXT (max 100) | REQUIRED |
| `contactInfo.supportPhoneNumber` | Support phone number | TEXT (max 30) | REQUIRED |

### US_TEN_DLC_BRAND_VETTING

No field definitions — create, associate the brand, and submit.

### US_TEN_DLC_CAMPAIGN_REGISTRATION

| FieldPath | Title | Type | Requirement |
|-----------|-------|------|-------------|
| `campaignInfo.campaignName` | Campaign description | TEXT (40-4096) | REQUIRED |
| `campaignInfo.vertical` | Vertical | SELECT | REQUIRED |
| `campaignInfo.termsAndConditionsLink` | T&C URL | TEXT (max 255) | OPTIONAL |
| `campaignInfo.termsAndConditionsFile` | T&C file | ATTACHMENT | OPTIONAL |
| `campaignInfo.privacyPolicyLink` | Privacy policy URL | TEXT (max 255) | OPTIONAL |
| `campaignInfo.privacyPolicyFile` | Privacy policy file | ATTACHMENT | OPTIONAL |
| `campaignInfo.optInWorkflow` | Opt-in workflow | TEXT (40-2048) | REQUIRED |
| `campaignInfo.optInScreenshot` | Opt-in screenshot | ATTACHMENT | OPTIONAL |
| `campaignInfo.optInKeyword` | Opt-in keyword | TEXT (max 255) | OPTIONAL |
| `campaignInfo.optInMessage` | Opt-in confirmation message | TEXT (20-255) | REQUIRED |
| `campaignInfo.helpMessage` | HELP message | TEXT (20-255) | REQUIRED |
| `campaignInfo.stopMessage` | STOP message | TEXT (20-255) | REQUIRED |
| `campaignCapabilities.numberCapabilities` | Number capabilities | SELECT | REQUIRED |
| `campaignCapabilities.messageType` | Message type | SELECT | OPTIONAL |
| `campaignUseCase.useCase` | Use case | SELECT | REQUIRED |
| `campaignUseCase.subUseCases` | Sub use cases | SELECT (1-5) | OPTIONAL |
| `campaignUseCase.subscriberOptIn` | Subscriber opt-in | SELECT ("Yes") | REQUIRED |
| `campaignUseCase.subscriberOptOut` | Subscriber opt-out | SELECT ("Yes") | REQUIRED |
| `campaignUseCase.subscriberHelp` | Subscriber help | SELECT ("Yes") | REQUIRED |
| `campaignUseCase.directLending` | Direct lending | SELECT | REQUIRED |
| `campaignUseCase.embeddedLink` | Embedded link | SELECT | REQUIRED |
| `campaignUseCase.embeddedLinkSample` | Embedded link sample | TEXT (max 255) | OPTIONAL |
| `campaignUseCase.embeddedPhone` | Embedded phone number | SELECT | REQUIRED |
| `campaignUseCase.ageGated` | Age-gated content | SELECT | REQUIRED |
| `messageSamples.messageSample1` | Message sample 1 | TEXT (20-1024) | REQUIRED |
| `messageSamples.messageSample2` | Message sample 2 | TEXT (20-1024) | OPTIONAL |
| `messageSamples.messageSample3` | Message sample 3 | TEXT (20-1024) | OPTIONAL |
| `messageSamples.messageSample4` | Message sample 4 | TEXT (20-1024) | OPTIONAL |
| `messageSamples.messageSample5` | Message sample 5 | TEXT (20-1024) | OPTIONAL |
| `mmsFileSamples.mmsFileSample1-5` | MMS file samples | ATTACHMENT | OPTIONAL |

---

## Timeline Summary

| Step | Action | Expected Duration |
|------|--------|-------------------|
| 1-3 | Brand registration + submission | Approval typically within 24-48 hours |
| 4 | Brand vetting (optional) | Varies, typically a few business days |
| 5-7 | Campaign registration + submission | Approval can be instant or up to 4 weeks |
| 8-9 | Phone number request + association | Number provisioned immediately; carrier review 4-6 weeks |

---

## Additional Resources

- [10DLC Registration Best Practices](https://aws.amazon.com/blogs/messaging-and-targeting/10dlc-registration-best-practices-to-send-sms-with-amazon-pinpoint/)
- [How to Build a Compliant SMS Opt-In Process](https://aws.amazon.com/blogs/messaging-and-targeting/how-to-build-a-compliant-sms-opt-in-process-with-amazon-pinpoint/)
- [AWS End User Messaging SMS User Guide — Registrations](https://docs.aws.amazon.com/sms-voice/latest/userguide/registrations.html)
- [AWS End User Messaging Pricing](https://aws.amazon.com/end-user-messaging/pricing/)
- [CLI Reference: pinpoint-sms-voice-v2](https://docs.aws.amazon.com/cli/latest/reference/pinpoint-sms-voice-v2/)
