"""
Intake Lambda — receives form submission from API Gateway,
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


def handler(event, context):
    body = json.loads(event.get('body', '{}'))

    request_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + 'Z'

    # Store the full registration request in DynamoDB
    item = {
        'requestId': request_id,
        'status': 'SUBMITTED',
        'createdAt': now,
        'updatedAt': now,
        'enableVetting': body.get('enableVetting', False),
        # Brand fields
        'brandFields': body.get('brandFields', {}),
        # Campaign fields
        'campaignFields': body.get('campaignFields', {}),
        # Attachment S3 keys
        'attachments': body.get('attachments', {}),
        # Phone number config
        'phoneConfig': body.get('phoneConfig', {}),
        # Will be populated as registrations are created
        'brandRegId': '-',
        'campaignRegId': '-',
        'vettingRegId': '-',
        'phoneNumberId': '-',
        'attachmentIds': {},
        'taskTokens': {},
    }
    table.put_item(Item=item)

    # Start Step Functions execution
    sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=f'reg-{request_id}',
        input=json.dumps({
            'requestId': request_id,
            'enableVetting': body.get('enableVetting', False),
        })
    )

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'requestId': request_id,
            'message': 'Registration workflow started',
        })
    }
