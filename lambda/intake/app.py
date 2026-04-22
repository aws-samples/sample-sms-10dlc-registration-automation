# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""
Intake Lambda -- receives form submission from API Gateway,
writes to DynamoDB, and starts Step Functions execution.
"""
import json
import os
import uuid
from datetime import datetime

import boto3

dynamodb = boto3.resource('dynamodb')
sfn = boto3.client('stepfunctions')
table = dynamodb.Table(os.environ['REGISTRATIONS_TABLE'])
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']

REQUIRED_BRAND_FIELDS = ['companyName', 'taxId', 'address', 'city', 'state', 'zipCode']


def handler(event, context):
    # Parse body
    try:
        body = json.loads(event.get('body', '{}'))
    except (json.JSONDecodeError, TypeError) as exc:
        return _error(400, f'Invalid JSON in request body: {exc}')

    # Validate brandFields
    brand_fields = body.get('brandFields')
    if not brand_fields or not isinstance(brand_fields, dict):
        return _error(400, 'brandFields is required and must be an object')

    # Validate campaignFields
    campaign_fields = body.get('campaignFields')
    if not campaign_fields or not isinstance(campaign_fields, dict):
        return _error(400, 'campaignFields is required and must be an object')

    # Check required brand fields
    missing = [f for f in REQUIRED_BRAND_FIELDS if not brand_fields.get(f)]
    if missing:
        return _error(400, f'Missing required brand fields: {", ".join(missing)}')

    request_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + 'Z'

    # Store the full registration request in DynamoDB
    item = {
        'requestId': request_id,
        'status': 'SUBMITTED',
        'createdAt': now,
        'updatedAt': now,
        'enableVetting': body.get('enableVetting', False),
        'brandFields': brand_fields,
        'campaignFields': campaign_fields,
        'attachments': body.get('attachments', {}),
        'phoneConfig': body.get('phoneConfig', {}),
        # Will be populated as registrations are created
        'brandRegId': '-',
        'campaignRegId': '-',
        'vettingRegId': '-',
        'phoneNumberId': '-',
        'attachmentIds': {},
        'taskTokens': {},
    }

    try:
        table.put_item(Item=item)
    except Exception as exc:
        return _error(500, f'Failed to store registration: {exc}')

    try:
        sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f'reg-{request_id}',
            input=json.dumps({
                'requestId': request_id,
                'enableVetting': body.get('enableVetting', False),
            })
        )
    except Exception as exc:
        return _error(500, f'Failed to start workflow: {exc}')

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'requestId': request_id,
            'message': 'Registration workflow started',
        })
    }


def _error(status_code, message):
    """Return an API Gateway-compatible error response."""
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': message}),
    }
