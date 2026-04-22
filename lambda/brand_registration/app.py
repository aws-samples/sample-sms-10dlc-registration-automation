# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""
Brand Registration Lambda -- creates the brand registration,
populates all fields, submits, and stores task tokens for callbacks.
"""
import json
import os

import boto3

from dry_run import is_dry_run, fake_create_registration

dynamodb = boto3.resource('dynamodb')
sms = boto3.client('pinpoint-sms-voice-v2')
table = dynamodb.Table(os.environ['REGISTRATIONS_TABLE'])

# Brand field mappings: form field name -> (FieldPath, value_type)
# value_type: 'text' uses --text-value, 'select' uses --text-choices
COMPANY_INFO_FIELDS = {
    'companyName':          ('companyInfo.companyName', 'text'),
    'taxIdIssuingCountry':  ('companyInfo.taxIdIssuingCountry', 'text'),
    'taxId':                ('companyInfo.taxId', 'text'),
    'legalType':            ('companyInfo.legalType', 'select'),
    'stockSymbol':          ('companyInfo.stockSymbol', 'text'),
    'stockExchange':        ('companyInfo.stockExchange', 'select'),
    'businessContactEmail': ('companyInfo.businessContactEmail', 'text'),
    'address':              ('companyInfo.address', 'text'),
    'city':                 ('companyInfo.city', 'text'),
    'state':                ('companyInfo.state', 'text'),
    'zipCode':              ('companyInfo.zipCode', 'text'),
    'isoCountryCode':       ('companyInfo.isoCountryCode', 'text'),
}

CONTACT_INFO_FIELDS = {
    'dbaName':              ('contactInfo.dbaName', 'text'),
    'contactVertical':      ('contactInfo.vertical', 'select'),
    'website':              ('contactInfo.website', 'text'),
    'supportEmail':         ('contactInfo.supportEmail', 'text'),
    'supportPhoneNumber':   ('contactInfo.supportPhoneNumber', 'text'),
}


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
    """Store the Step Functions task token in DynamoDB for EventBridge callback."""
    task_token = payload['taskToken']
    waiting_for = payload['waitingFor']

    table.update_item(
        Key={'requestId': request_id},
        UpdateExpression='SET taskTokens.#wf = :token, updatedAt = :now',
        ExpressionAttributeNames={'#wf': waiting_for},
        ExpressionAttributeValues={
            ':token': task_token,
            ':now': _now(),
        }
    )
    # This Lambda is invoked with .waitForTaskToken -- it does NOT return.
    # Step Functions will pause until SendTaskSuccess/Failure is called.


def create_and_submit(request_id):
    """Create brand registration, populate fields, and submit."""
    dry = is_dry_run()

    # Fetch form data from DynamoDB
    item = table.get_item(Key={'requestId': request_id})['Item']
    brand_fields = item.get('brandFields', {})

    # 1. Create the registration
    if not dry:
        resp = sms.create_registration(
            RegistrationType='US_TEN_DLC_BRAND_REGISTRATION',
            Tags=[{'Key': 'Name', 'Value': brand_fields.get('companyName', 'Brand')}]
        )
    else:
        resp = fake_create_registration('US_TEN_DLC_BRAND_REGISTRATION')
    brand_reg_id = resp['RegistrationId']

    # Save the brand reg ID to DynamoDB
    table.update_item(
        Key={'requestId': request_id},
        UpdateExpression='SET brandRegId = :rid, #s = :status, updatedAt = :now',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':rid': brand_reg_id,
            ':status': 'BRAND_CREATED',
            ':now': _now(),
        }
    )

    if not dry:
        # 2. Populate companyInfo fields
        for form_key, (field_path, val_type) in COMPANY_INFO_FIELDS.items():
            value = brand_fields.get(form_key)
            if value:
                _put_field(brand_reg_id, field_path, value, val_type)

        # 3. Populate contactInfo fields
        for form_key, (field_path, val_type) in CONTACT_INFO_FIELDS.items():
            value = brand_fields.get(form_key)
            if value:
                _put_field(brand_reg_id, field_path, value, val_type)

        # 4. Submit
        sms.submit_registration_version(RegistrationId=brand_reg_id)

    table.update_item(
        Key={'requestId': request_id},
        UpdateExpression='SET #s = :status, updatedAt = :now',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':status': 'BRAND_SUBMITTED',
            ':now': _now(),
        }
    )

    return {'brandRegId': brand_reg_id, 'status': 'BRAND_SUBMITTED'}


def _put_field(reg_id, field_path, value, val_type):
    """Set a single registration field value."""
    params = {
        'RegistrationId': reg_id,
        'FieldPath': field_path,
    }
    if val_type == 'select':
        params['TextChoices'] = [value] if isinstance(value, str) else value
    else:
        params['TextValue'] = value

    sms.put_registration_field_value(**params)


def _now():
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'
