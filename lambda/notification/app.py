# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""
Notification Lambda - sends SNS alerts for registration status changes.
Pulls additional context from DynamoDB and the AWS End User Messaging SMS
API to provide actionable notifications with specific rejection reasons.
"""
import json
import os

import boto3

sns = boto3.client('sns')
sms = boto3.client('pinpoint-sms-voice-v2')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['REGISTRATIONS_TABLE'])
TOPIC_ARN = os.environ['NOTIFICATION_TOPIC_ARN']
DRY_RUN = os.environ.get('DRY_RUN', 'false').lower() == 'true'

SUBJECTS = {
    'BRAND_SUBMITTED': '[INFO] 10DLC Brand Registration Submitted',
    'VETTING_SUBMITTED': '[INFO] 10DLC Brand Vetting Submitted',
    'CAMPAIGN_SUBMITTED': '[INFO] 10DLC Campaign Registration Submitted',
    'BRAND_REJECTED': '[WARNING] 10DLC Brand Registration Requires Updates',
    'VETTING_FAILED': '[WARNING] 10DLC Brand Vetting Did Not Pass - Action Required',
    'CAMPAIGN_REJECTED': '[WARNING] 10DLC Campaign Registration Requires Updates',
    'REGISTRATION_COMPLETE': '[SUCCESS] 10DLC Registration Complete - Ready to Send',
    'REGISTRATION_TIMED_OUT': '[ERROR] 10DLC Registration Timed Out',
}


def handler(event, context):
    payload = event.get('Payload', event)
    request_id = payload.get('requestId', 'unknown')
    notification_type = payload.get('type', 'UNKNOWN')
    error = payload.get('error', {})
    phone_result = payload.get('phoneResult', {})

    item = _get_item(request_id)

    subject = SUBJECTS.get(notification_type, f'10DLC Registration Update: {notification_type}')
    message = build_message(request_id, notification_type, error, item, phone_result)

    sns.publish(
        TopicArn=TOPIC_ARN,
        Subject=subject[:100],
        Message=message,
    )

    return {'notified': True, 'type': notification_type}


def _get_item(request_id):
    try:
        resp = table.get_item(Key={'requestId': request_id})
        return resp.get('Item', {})
    except Exception:
        return {}


def _get_rejection_details(registration_id):
    if DRY_RUN or not registration_id or registration_id == '-':
        return None, []

    version_reason = None
    denied_fields = []

    try:
        resp = sms.describe_registration_versions(RegistrationId=registration_id)
        versions = resp.get('RegistrationVersions', [])
        if versions:
            latest = versions[-1]
            version_reason = latest.get('DeniedReasonMessage')
    except Exception as e:
        print(f'Warning: Could not fetch registration versions for {registration_id}: {e}')

    try:
        paginator = sms.get_paginator('describe_registration_field_values')
        for page in paginator.paginate(RegistrationId=registration_id):
            for field in page.get('RegistrationFieldValues', []):
                denied_reason = field.get('DeniedReason')
                if denied_reason:
                    denied_fields.append({
                        'fieldPath': field.get('FieldPath', 'unknown'),
                        'reason': denied_reason,
                    })
    except Exception as e:
        print(f'Warning: Could not fetch field values for {registration_id}: {e}')

    return version_reason, denied_fields


def _format_rejection_details(registration_id):
    version_reason, denied_fields = _get_rejection_details(registration_id)
    lines = []

    if version_reason or denied_fields:
        lines.append('')
        lines.append('REJECTION DETAILS (from carrier/TCR):')
        lines.append('-' * 30)

    if version_reason:
        lines.append(f'  Reason: {version_reason}')
        lines.append('')

    if denied_fields:
        lines.append('  Fields requiring correction:')
        for df in denied_fields:
            lines.append(f'    - {df["fieldPath"]}')
            lines.append(f'      Reason: {df["reason"]}')
        lines.append('')
    elif not version_reason:
        lines.append('')
        lines.append('  (No specific rejection details available from the API.')
        lines.append('   Check the registration in the AWS console for details.)')
        lines.append('')

    return lines


def build_message(request_id, notification_type, error, item, phone_result):
    brand_fields = item.get('brandFields', {})
    campaign_fields = item.get('campaignFields', {})
    company_name = brand_fields.get('companyName', 'Unknown')
    brand_reg_id = item.get('brandRegId', '-')
    campaign_reg_id = item.get('campaignRegId', '-')
    vetting_reg_id = item.get('vettingRegId', '-')

    lines = [
        '10DLC Registration Update',
        '=' * 50,
        '',
        f'Request ID:   {request_id}',
        f'Company:      {company_name}',
        f'Event:        {notification_type}',
        '',
    ]

    if notification_type == 'BRAND_SUBMITTED':
        lines.extend(_brand_submitted(request_id, item))
    elif notification_type == 'VETTING_SUBMITTED':
        lines.extend(_vetting_submitted(request_id, item))
    elif notification_type == 'CAMPAIGN_SUBMITTED':
        lines.extend(_campaign_submitted(request_id, item))
    elif notification_type == 'BRAND_REJECTED':
        lines.extend(_brand_rejected(request_id, brand_reg_id, company_name))
    elif notification_type == 'VETTING_FAILED':
        lines.extend(_vetting_failed(request_id, vetting_reg_id, company_name))
    elif notification_type == 'CAMPAIGN_REJECTED':
        lines.extend(_campaign_rejected(request_id, campaign_reg_id, campaign_fields))
    elif notification_type == 'REGISTRATION_COMPLETE':
        lines.extend(_registration_complete(request_id, item, phone_result))
    elif notification_type == 'REGISTRATION_TIMED_OUT':
        lines.extend(_registration_timed_out(request_id, item, error))

    lines.extend([
        '',
        '-' * 50,
        'AWS End User Messaging SMS Console:',
        '  https://console.aws.amazon.com/sms-voice/home#/registrations',
        '',
        'This is an automated notification from the 10DLC Registration Automation workflow.',
    ])

    return '\n'.join(lines)


def _brand_submitted(request_id, item):
    """Build brand submission confirmation."""
    brand_reg_id = item.get('brandRegId', '-')
    company_name = item.get('brandFields', {}).get('companyName', 'Unknown')
    tax_id = item.get('brandFields', {}).get('taxId', '-')
    return [
        'BRAND REGISTRATION SUBMITTED SUCCESSFULLY',
        '-' * 30,
        '',
        'Your 10DLC brand registration has been submitted for review.',
        'No action is needed — you will be notified when the review is complete.',
        '',
        'Details:',
        f'  Company:       {company_name}',
        f'  Brand Reg ID:  {brand_reg_id}',
        f'  Tax ID (EIN):  {tax_id}',
        '',
        'What happens next:',
        '  - Brand review typically completes within minutes to a few hours',
        '  - You will receive an email when the brand is approved or rejected',
        '  - If approved, the workflow automatically proceeds to campaign registration',
        '  - If vetting is enabled, it will run after brand approval',
    ]


def _vetting_submitted(request_id, item):
    """Build vetting submission confirmation."""
    vetting_reg_id = item.get('vettingRegId', '-')
    company_name = item.get('brandFields', {}).get('companyName', 'Unknown')
    return [
        'BRAND VETTING SUBMITTED SUCCESSFULLY',
        '-' * 30,
        '',
        'Your 10DLC brand vetting request has been submitted.',
        'No action is needed — you will be notified when vetting completes.',
        '',
        'Details:',
        f'  Company:        {company_name}',
        f'  Vetting Reg ID: {vetting_reg_id}',
        '',
        'What happens next:',
        '  - Vetting is performed by a third party and typically takes a few business days',
        '  - Passing vetting increases your throughput limits significantly',
        '  - If vetting fails, you can still proceed with standard (lower) limits',
        '  - You will receive an email with the result either way',
    ]


def _campaign_submitted(request_id, item):
    """Build campaign submission confirmation."""
    campaign_reg_id = item.get('campaignRegId', '-')
    campaign_fields = item.get('campaignFields', {})
    use_case = campaign_fields.get('useCase', '-')
    campaign_name = campaign_fields.get('campaignName', '-')
    return [
        'CAMPAIGN REGISTRATION SUBMITTED SUCCESSFULLY',
        '-' * 30,
        '',
        'Your 10DLC campaign registration has been submitted for review.',
        'No action is needed — you will be notified when the review is complete.',
        '',
        'Details:',
        f'  Campaign Name:   {campaign_name}',
        f'  Campaign Reg ID: {campaign_reg_id}',
        f'  Use Case:        {use_case}',
        '',
        'What happens next:',
        '  - Campaign review can take up to 4-6 weeks',
        '  - You will receive an email when the campaign is approved or rejected',
        '  - If approved, a phone number will be provisioned and associated automatically',
        '  - You will receive a final completion email with the phone number details',
    ]


def _brand_rejected(request_id, brand_reg_id, company_name):
    lines = [
        'BRAND REGISTRATION REJECTED',
        '-' * 30,
        '',
        f'Brand Reg ID: {brand_reg_id}',
        f'Company:      {company_name}',
        '',
        'The brand registration was rejected and requires corrections.',
    ]
    lines.extend(_format_rejection_details(brand_reg_id))
    lines.extend([
        'Common reasons for brand rejection:',
        '  - Company name does not match EIN/tax records',
        '  - Invalid or mismatched tax ID (EIN)',
        '  - Website URL is unreachable or does not match the company',
        '  - Support email or phone number is invalid',
        '  - Incorrect legal entity type selected',
        '',
        'To fix:',
        '  1. Open the registration in the AWS End User Messaging SMS console',
        '  2. Review the rejection details on the registration page',
        '  3. Correct the flagged fields and resubmit',
        '  4. Resume the workflow:',
        f'     POST /api/resume/{request_id}',
        '',
        'The workflow is PAUSED and waiting for your action.',
    ])
    return lines


def _vetting_failed(request_id, vetting_reg_id, company_name):
    lines = [
        'BRAND VETTING DID NOT PASS - ACTION REQUIRED',
        '-' * 30,
        '',
        f'Vetting Reg ID: {vetting_reg_id}',
        f'Company:        {company_name}',
        '',
        'The third-party brand vetting check did not pass.',
        'This does NOT block your campaign - but it affects your throughput.',
    ]
    lines.extend(_format_rejection_details(vetting_reg_id))
    lines.extend([
        'WITHOUT vetting (current):',
        '  AT&T:     0.2 messages/second (MPS)',
        '  T-Mobile: 2,000 messages/day',
        '',
        'WITH vetting (if it had passed):',
        '  Up to 75 MPS (varies by use case and score)',
        '',
        'You have two options:',
        '',
        '  Option 1: PROCEED with unvetted (lower) limits',
        '    The campaign still works, just with reduced throughput.',
        '    Resume the workflow:',
        f'      POST /api/resume/{request_id}',
        '',
        '  Option 2: RETRY vetting before proceeding',
        '    Submit a new vetting request in the AWS End User Messaging SMS console.',
        '    Vetting costs $40 and takes a few business days.',
        '    Once it passes, resume the workflow with the same endpoint.',
        '',
        'The workflow is PAUSED and waiting for your decision.',
    ])
    return lines


def _campaign_rejected(request_id, campaign_reg_id, campaign_fields):
    use_case = campaign_fields.get('useCase', 'Unknown')
    campaign_name = campaign_fields.get('campaignName', 'Unknown')
    lines = [
        'CAMPAIGN REGISTRATION REJECTED',
        '-' * 30,
        '',
        f'Campaign Reg ID: {campaign_reg_id}',
        f'Campaign Name:   {campaign_name}',
        f'Use Case:        {use_case}',
        '',
        'The campaign registration was rejected and requires corrections.',
    ]
    lines.extend(_format_rejection_details(campaign_reg_id))
    lines.extend([
        'Common reasons for campaign rejection:',
        '  - Message samples do not match the declared use case',
        '  - Opt-in workflow description is insufficient or unclear',
        '  - Opt-in screenshot does not show clear consent language',
        '  - Terms and conditions or privacy policy links are broken',
        '  - HELP/STOP message content does not meet carrier requirements',
        '  - Embedded links or phone numbers not declared correctly',
        '',
        'To fix:',
        '  1. Open the campaign registration in the AWS End User Messaging SMS console',
        '  2. Review the rejection details on the registration page',
        '  3. Correct the flagged fields and resubmit',
        '  4. Resume the workflow:',
        f'     POST /api/resume/{request_id}',
        '',
        'The workflow is PAUSED and waiting for your action.',
    ])
    return lines


def _registration_complete(request_id, item, phone_result):
    brand_reg_id = item.get('brandRegId', '-')
    campaign_reg_id = item.get('campaignRegId', '-')
    vetting_reg_id = item.get('vettingRegId', '-')
    company_name = item.get('brandFields', {}).get('companyName', 'Unknown')
    use_case = item.get('campaignFields', {}).get('useCase', 'Unknown')

    phone_payload = phone_result.get('Payload', phone_result)
    phone_number = phone_payload.get('phoneNumber', item.get('phoneNumber', '-'))
    phone_number_id = phone_payload.get('phoneNumberId', item.get('phoneNumberId', '-'))

    vetted = vetting_reg_id != '-'

    lines = [
        'REGISTRATION COMPLETE - READY TO SEND',
        '-' * 30,
        '',
        'Your 10DLC registration is fully complete. All components are',
        'provisioned and associated. You can now send messages.',
        '',
        'Summary:',
        f'  Company:         {company_name}',
        f'  Brand Reg ID:    {brand_reg_id}',
        f'  Campaign Reg ID: {campaign_reg_id}',
        f'  Use Case:        {use_case}',
        f'  Vetting:         {"Yes" if vetted else "No (standard throughput limits)"}',
        '',
        'Phone Number:',
        f'  Number:    {phone_number}',
        f'  Number ID: {phone_number_id}',
        '',
        'Next steps:',
        '  - Use the phone number above as your origination identity',
        '  - Messages must match the declared use case and samples',
        '  - Monitor delivery rates in the AWS End User Messaging SMS console',
    ]

    if not vetted:
        lines.extend([
            '',
            'Note: This campaign is UNVETTED. Throughput limits:',
            '  AT&T:     0.2 messages/second (MPS)',
            '  T-Mobile: 2,000 messages/day',
            '  You can submit vetting separately at any time to increase limits.',
        ])

    return lines


def _registration_timed_out(request_id, item, error):
    brand_reg_id = item.get('brandRegId', '-')
    campaign_reg_id = item.get('campaignRegId', '-')
    status = item.get('status', 'UNKNOWN')
    return [
        'REGISTRATION TIMED OUT',
        '-' * 30,
        '',
        'The registration workflow timed out waiting for approval.',
        '',
        'Last known state:',
        f'  Status:          {status}',
        f'  Brand Reg ID:    {brand_reg_id}',
        f'  Campaign Reg ID: {campaign_reg_id}',
        '',
        'This usually means a registration has been sitting in review',
        'longer than expected (30 days for brand/vetting, 60 days for campaign).',
        '',
        'To investigate:',
        '  1. Check the registration status in the AWS End User Messaging SMS console',
        '  2. If still under review, contact AWS Support',
        '  3. If rejected, fix and resubmit, then start a new workflow',
        '',
        f'Error: {json.dumps(error, indent=2)}',
    ]
