"""
Notification Lambda — sends SNS alerts for registration status changes.
"""
import json
import os

import boto3

sns = boto3.client('sns')
TOPIC_ARN = os.environ['NOTIFICATION_TOPIC_ARN']

SUBJECTS = {
    'BRAND_REJECTED': '⚠️ 10DLC Brand Registration Requires Updates',
    'VETTING_FAILED': 'ℹ️ 10DLC Brand Vetting Did Not Pass',
    'CAMPAIGN_REJECTED': '⚠️ 10DLC Campaign Registration Requires Updates',
    'REGISTRATION_COMPLETE': '✅ 10DLC Registration Complete',
    'REGISTRATION_TIMED_OUT': '❌ 10DLC Registration Timed Out',
}


def handler(event, context):
    payload = event.get('Payload', event)
    request_id = payload.get('requestId', 'unknown')
    notification_type = payload.get('type', 'UNKNOWN')
    error = payload.get('error', {})

    subject = SUBJECTS.get(notification_type, f'10DLC Registration Update: {notification_type}')

    message = build_message(request_id, notification_type, error)

    sns.publish(
        TopicArn=TOPIC_ARN,
        Subject=subject[:100],  # SNS subject max 100 chars
        Message=message,
    )

    return {'notified': True, 'type': notification_type}


def build_message(request_id, notification_type, error):
    lines = [
        f'10DLC Registration Update',
        f'========================',
        f'Request ID: {request_id}',
        f'Event: {notification_type}',
        '',
    ]

    if notification_type == 'BRAND_REJECTED':
        lines.extend([
            'Your brand registration requires updates before it can be approved.',
            'Please review the registration in the AWS End User Messaging SMS console,',
            'make the necessary corrections, and resubmit.',
            '',
            'Once fixed, call the resume endpoint:',
            f'  POST /api/resume/{request_id}',
            '',
            f'Error details: {json.dumps(error, indent=2)}',
        ])
    elif notification_type == 'CAMPAIGN_REJECTED':
        lines.extend([
            'Your campaign registration requires updates.',
            'Please review the campaign in the AWS End User Messaging SMS console,',
            'make corrections, and resubmit.',
            '',
            'Once fixed, call the resume endpoint:',
            f'  POST /api/resume/{request_id}',
            '',
            f'Error details: {json.dumps(error, indent=2)}',
        ])
    elif notification_type == 'VETTING_FAILED':
        lines.extend([
            'Brand vetting did not pass. This is non-blocking — your campaign',
            'will proceed with standard (unvetted) throughput limits:',
            '  - 75 msg/min to AT&T',
            '  - 2,000 msg/day to T-Mobile',
            '',
            'You can retry vetting separately if needed.',
        ])
    elif notification_type == 'REGISTRATION_COMPLETE':
        lines.extend([
            'Your 10DLC registration is fully complete!',
            'Brand, campaign, and phone number are all provisioned and associated.',
            'You can now send messages using your 10DLC number.',
        ])
    elif notification_type == 'REGISTRATION_TIMED_OUT':
        lines.extend([
            'The registration workflow timed out waiting for approval.',
            'Please check the registration status in the AWS console.',
            '',
            f'Error: {json.dumps(error, indent=2)}',
        ])

    return '\n'.join(lines)
