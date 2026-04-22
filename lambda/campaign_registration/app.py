# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""
Campaign Registration Lambda -- creates campaign registration,
associates brand, populates all fields (including attachments), and submits.
"""
import json
import os

import boto3

from dry_run import is_dry_run, fake_create_registration

dynamodb = boto3.resource('dynamodb')
sms = boto3.client('pinpoint-sms-voice-v2')
table = dynamodb.Table(os.environ['REGISTRATIONS_TABLE'])
BUCKET = os.environ['UPLOAD_BUCKET']

# Campaign field mappings: form key -> (FieldPath, value_type)
CAMPAIGN_INFO_TEXT_FIELDS = {
    'campaignName':           ('campaignInfo.campaignName', 'text'),
    'termsAndConditionsLink': ('campaignInfo.termsAndConditionsLink', 'text'),
    'privacyPolicyLink':      ('campaignInfo.privacyPolicyLink', 'text'),
    'optInWorkflow':          ('campaignInfo.optInWorkflow', 'text'),
    'optInKeyword':           ('campaignInfo.optInKeyword', 'text'),
    'optInMessage':           ('campaignInfo.optInMessage', 'text'),
    'helpMessage':            ('campaignInfo.helpMessage', 'text'),
    'stopMessage':            ('campaignInfo.stopMessage', 'text'),
}

CAMPAIGN_INFO_SELECT_FIELDS = {
    'campaignVertical': ('campaignInfo.vertical', 'select'),
}

CAPABILITIES_FIELDS = {
    'numberCapabilities': ('campaignCapabilities.numberCapabilities', 'select'),
    'messageType':        ('campaignCapabilities.messageType', 'select'),
}

USE_CASE_SELECT_FIELDS = {
    'useCase':        ('campaignUseCase.useCase', 'select'),
    'subscriberOptIn':  ('campaignUseCase.subscriberOptIn', 'select'),
    'subscriberOptOut': ('campaignUseCase.subscriberOptOut', 'select'),
    'subscriberHelp':   ('campaignUseCase.subscriberHelp', 'select'),
    'directLending':    ('campaignUseCase.directLending', 'select'),
    'embeddedLink':     ('campaignUseCase.embeddedLink', 'select'),
    'embeddedPhone':    ('campaignUseCase.embeddedPhone', 'select'),
    'ageGated':         ('campaignUseCase.ageGated', 'select'),
}

USE_CASE_TEXT_FIELDS = {
    'embeddedLinkSample': ('campaignUseCase.embeddedLinkSample', 'text'),
}

# Attachment fields: form key -> FieldPath
ATTACHMENT_FIELDS = {
    'optInScreenshot':       'campaignInfo.optInScreenshot',
    'termsAndConditionsFile': 'campaignInfo.termsAndConditionsFile',
    'privacyPolicyFile':     'campaignInfo.privacyPolicyFile',
}

MESSAGE_SAMPLE_FIELDS = [
    ('messageSample1', 'messageSamples.messageSample1'),
    ('messageSample2', 'messageSamples.messageSample2'),
    ('messageSample3', 'messageSamples.messageSample3'),
    ('messageSample4', 'messageSamples.messageSample4'),
    ('messageSample5', 'messageSamples.messageSample5'),
]


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
    dry = is_dry_run()

    item = table.get_item(Key={'requestId': request_id})['Item']
    brand_reg_id = item['brandRegId']
    campaign_fields = item.get('campaignFields', {})
    attachments = item.get('attachments', {})

    # 1. Create campaign registration
    if not dry:
        resp = sms.create_registration(
            RegistrationType='US_TEN_DLC_CAMPAIGN_REGISTRATION',
            Tags=[{'Key': 'Name', 'Value': f'{request_id}-Campaign'}]
        )
    else:
        resp = fake_create_registration('US_TEN_DLC_CAMPAIGN_REGISTRATION')
    campaign_reg_id = resp['RegistrationId']

    if not dry:
        # 2. Associate brand (ASSOCIATE_BEFORE_SUBMIT)
        sms.create_registration_association(
            RegistrationId=campaign_reg_id,
            ResourceId=brand_reg_id,
        )

        # 3. Populate text fields
        for form_key, (field_path, val_type) in CAMPAIGN_INFO_TEXT_FIELDS.items():
            value = campaign_fields.get(form_key)
            if value:
                _put_field(campaign_reg_id, field_path, value, val_type)

        # 4. Populate select fields
        for form_key, (field_path, val_type) in CAMPAIGN_INFO_SELECT_FIELDS.items():
            value = campaign_fields.get(form_key)
            if value:
                _put_field(campaign_reg_id, field_path, value, val_type)

        for form_key, (field_path, val_type) in CAPABILITIES_FIELDS.items():
            value = campaign_fields.get(form_key)
            if value:
                _put_field(campaign_reg_id, field_path, value, val_type)

        for form_key, (field_path, val_type) in USE_CASE_SELECT_FIELDS.items():
            value = campaign_fields.get(form_key)
            if value:
                _put_field(campaign_reg_id, field_path, value, val_type)

        for form_key, (field_path, val_type) in USE_CASE_TEXT_FIELDS.items():
            value = campaign_fields.get(form_key)
            if value:
                _put_field(campaign_reg_id, field_path, value, val_type)

        # Sub use cases (multi-select)
        sub_use_cases = campaign_fields.get('subUseCases')
        if sub_use_cases and isinstance(sub_use_cases, list):
            sms.put_registration_field_value(
                RegistrationId=campaign_reg_id,
                FieldPath='campaignUseCase.subUseCases',
                TextChoices=sub_use_cases,
            )

        # 5. Handle attachments -- create attachment from S3, then set field value
        attachment_ids = {}
        for form_key, field_path in ATTACHMENT_FIELDS.items():
            s3_key = attachments.get(form_key)
            if s3_key:
                s3_url = f's3://{BUCKET}/{s3_key}'
                attach_resp = sms.create_registration_attachment(
                    AttachmentUrl=s3_url
                )
                attach_id = attach_resp['RegistrationAttachmentId']
                attachment_ids[form_key] = attach_id
                sms.put_registration_field_value(
                    RegistrationId=campaign_reg_id,
                    FieldPath=field_path,
                    RegistrationAttachmentId=attach_id,
                )

        # 6. Message samples
        for form_key, field_path in MESSAGE_SAMPLE_FIELDS:
            value = campaign_fields.get(form_key)
            if value:
                _put_field(campaign_reg_id, field_path, value, 'text')

        # 7. Submit
        sms.submit_registration_version(RegistrationId=campaign_reg_id)
    else:
        attachment_ids = {}

    # Update DynamoDB
    table.update_item(
        Key={'requestId': request_id},
        UpdateExpression='SET campaignRegId = :cid, attachmentIds = :aids, #s = :status, updatedAt = :now',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':cid': campaign_reg_id,
            ':aids': attachment_ids,
            ':status': 'CAMPAIGN_SUBMITTED',
            ':now': _now(),
        }
    )

    return {'campaignRegId': campaign_reg_id, 'status': 'CAMPAIGN_SUBMITTED'}


def _put_field(reg_id, field_path, value, val_type):
    params = {'RegistrationId': reg_id, 'FieldPath': field_path}
    if val_type == 'select':
        params['TextChoices'] = [value] if isinstance(value, str) else value
    else:
        params['TextValue'] = value
    sms.put_registration_field_value(**params)


def _now():
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'
