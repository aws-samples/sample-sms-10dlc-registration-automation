# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""
Phone Number Lambda -- requests a 10DLC phone number
and associates it with the approved campaign.
"""
import json
import os

import boto3

from dry_run import is_dry_run, fake_phone_number

dynamodb = boto3.resource('dynamodb')
sms = boto3.client('pinpoint-sms-voice-v2')
table = dynamodb.Table(os.environ['REGISTRATIONS_TABLE'])


def handler(event, context):
    dry = is_dry_run()

    payload = event.get('Payload', event)
    request_id = payload['requestId']

    item = table.get_item(Key={'requestId': request_id})['Item']
    campaign_reg_id = item['campaignRegId']
    phone_config = item.get('phoneConfig', {})

    message_type = phone_config.get('messageType', 'TRANSACTIONAL')
    capabilities = phone_config.get('capabilities', ['SMS'])

    # 1. Request a 10DLC phone number
    if not dry:
        resp = sms.request_phone_number(
            IsoCountryCode='US',
            MessageType=message_type,
            NumberCapabilities=capabilities,
            NumberType='TEN_DLC',
        )
    else:
        resp = fake_phone_number()
    phone_number_id = resp['PhoneNumberId']
    phone_number = resp.get('PhoneNumber', '')

    # 2. Associate with the campaign (ASSOCIATE_AFTER_COMPLETE)
    if not dry:
        sms.create_registration_association(
            RegistrationId=campaign_reg_id,
            ResourceId=phone_number_id,
        )

    # Update DynamoDB
    table.update_item(
        Key={'requestId': request_id},
        UpdateExpression='SET phoneNumberId = :pid, phoneNumber = :pn, #s = :status, updatedAt = :now',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':pid': phone_number_id,
            ':pn': phone_number,
            ':status': 'PHONE_ASSOCIATED',
            ':now': _now(),
        }
    )

    return {
        'phoneNumberId': phone_number_id,
        'phoneNumber': phone_number,
        'status': 'PHONE_ASSOCIATED',
    }


def _now():
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'
