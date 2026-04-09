"""
Vetting Lambda — creates brand vetting registration,
associates the approved brand, and submits.
"""
import json
import os

import boto3

dynamodb = boto3.resource('dynamodb')
sms = boto3.client('pinpoint-sms-voice-v2')
table = dynamodb.Table(os.environ['REGISTRATIONS_TABLE'])


def handler(event, context):
    payload = event.get('Payload', event)
    request_id = payload['requestId']
    action = payload.get('action')

    if action == 'store_task_token':
        return store_task_token(request_id, payload)

    if action == 'create_and_submit':
        return create_and_submit(request_id)

    return {'error': f'Unknown action: {action}'}


def store_task_token(request_id, payload):
    """Store task token for EventBridge callback."""
    table.update_item(
        Key={'requestId': request_id},
        UpdateExpression='SET taskTokens.#wf = :token, updatedAt = :now',
        ExpressionAttributeNames={'#wf': payload['waitingFor']},
        ExpressionAttributeValues={
            ':token': payload['taskToken'],
            ':now': _now(),
        }
    )


def create_and_submit(request_id):
    """Create vetting, associate brand, submit."""
    item = table.get_item(Key={'requestId': request_id})['Item']
    brand_reg_id = item['brandRegId']

    # 1. Create vetting registration
    resp = sms.create_registration(
        RegistrationType='US_TEN_DLC_BRAND_VETTING',
        Tags=[{'Key': 'Name', 'Value': f'{request_id}-Vetting'}]
    )
    vetting_reg_id = resp['RegistrationId']

    # 2. Associate the approved brand (ASSOCIATE_BEFORE_SUBMIT)
    sms.create_registration_association(
        RegistrationId=vetting_reg_id,
        ResourceId=brand_reg_id,
    )

    # 3. Submit
    sms.submit_registration_version(RegistrationId=vetting_reg_id)

    # Update DynamoDB
    table.update_item(
        Key={'requestId': request_id},
        UpdateExpression='SET vettingRegId = :vid, #s = :status, updatedAt = :now',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':vid': vetting_reg_id,
            ':status': 'VETTING_SUBMITTED',
            ':now': _now(),
        }
    )

    return {'vettingRegId': vetting_reg_id, 'status': 'VETTING_SUBMITTED'}


def _now():
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'
