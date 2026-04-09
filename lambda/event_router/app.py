"""
Event Router Lambda — receives EventBridge Registration Status Change events,
looks up the corresponding task token in DynamoDB, and calls
SendTaskSuccess or SendTaskFailure to resume the Step Functions execution.
"""
import json
import os

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
sfn = boto3.client('stepfunctions')
table = dynamodb.Table(os.environ['REGISTRATIONS_TABLE'])

# Statuses that mean "approved / done"
SUCCESS_STATUSES = {'COMPLETE', 'PROVISIONING'}
# Statuses that mean "needs human intervention"
FAILURE_STATUSES = {'REQUIRES_UPDATES', 'REQUIRES_AUTHENTICATION', 'CLOSED', 'DELETED'}
# Statuses we ignore (still in progress)
IGNORE_STATUSES = {'CREATED', 'SUBMITTED', 'REVIEWING'}


def handler(event, context):
    detail = event.get('detail', {})
    reg_details = detail.get('registrationDetails', {})
    registration_id = reg_details.get('registrationId', '')
    current_status = reg_details.get('currentStatus', '')
    reg_type = reg_details.get('registrationType', '')

    print(f'Event: regId={registration_id}, status={current_status}, type={reg_type}')

    if current_status in IGNORE_STATUSES:
        print(f'Ignoring status: {current_status}')
        return {'action': 'ignored'}

    # Look up the request by registration ID
    # Try brand index first, then campaign index
    item = _find_by_reg_id(registration_id)
    if not item:
        print(f'No matching request found for registration {registration_id}')
        return {'action': 'no_match'}

    request_id = item['requestId']
    task_tokens = item.get('taskTokens', {})

    # Determine which task token to use based on registration type
    token_key = _get_token_key(reg_type, item, registration_id)
    if not token_key:
        print(f'Could not determine token key for {reg_type}')
        return {'action': 'no_token_key'}

    task_token = task_tokens.get(token_key)
    if not task_token:
        print(f'No task token found for key: {token_key}')
        return {'action': 'no_token'}

    # Update status in DynamoDB
    table.update_item(
        Key={'requestId': request_id},
        UpdateExpression='SET #s = :status, updatedAt = :now',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':status': f'{token_key.upper()}_{current_status}',
            ':now': _now(),
        }
    )

    # Send callback to Step Functions
    if current_status in SUCCESS_STATUSES:
        sfn.send_task_success(
            taskToken=task_token,
            output=json.dumps({
                'registrationId': registration_id,
                'status': current_status,
            })
        )
        print(f'SendTaskSuccess for {token_key}')
    elif current_status in FAILURE_STATUSES:
        sfn.send_task_failure(
            taskToken=task_token,
            error=current_status,
            cause=f'Registration {registration_id} status: {current_status}',
        )
        print(f'SendTaskFailure for {token_key}: {current_status}')

    return {'action': 'callback_sent', 'status': current_status}


def _find_by_reg_id(registration_id):
    """Look up a request by brand or campaign registration ID."""
    # Try brand index
    resp = table.query(
        IndexName='brand-reg-index',
        KeyConditionExpression=Key('brandRegId').eq(registration_id),
    )
    if resp['Items']:
        return resp['Items'][0]

    # Try campaign index
    resp = table.query(
        IndexName='campaign-reg-index',
        KeyConditionExpression=Key('campaignRegId').eq(registration_id),
    )
    if resp['Items']:
        return resp['Items'][0]

    return None


def _get_token_key(reg_type, item, registration_id):
    """Map registration type to the task token key in DynamoDB."""
    if reg_type == 'US_TEN_DLC_BRAND_REGISTRATION':
        # Could be waiting for brand approval or human intervention
        tokens = item.get('taskTokens', {})
        if 'brand_human_intervention' in tokens:
            return 'brand_human_intervention'
        return 'brand'
    elif reg_type == 'US_TEN_DLC_BRAND_VETTING':
        return 'vetting'
    elif reg_type == 'US_TEN_DLC_CAMPAIGN_REGISTRATION':
        tokens = item.get('taskTokens', {})
        if 'campaign_human_intervention' in tokens:
            return 'campaign_human_intervention'
        return 'campaign'
    return None


def _now():
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'
