"""
Resume Lambda — human-in-the-loop endpoint.
After a rejection, the operator fixes the registration in the console
and calls this endpoint to resume the Step Functions workflow.
"""
import json
import os

import boto3

dynamodb = boto3.resource('dynamodb')
sfn = boto3.client('stepfunctions')
table = dynamodb.Table(os.environ['REGISTRATIONS_TABLE'])


def handler(event, context):
    request_id = event.get('pathParameters', {}).get('requestId')
    if not request_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'requestId is required'})
        }

    # Look up the request
    resp = table.get_item(Key={'requestId': request_id})
    item = resp.get('Item')
    if not item:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': f'Request {request_id} not found'})
        }

    task_tokens = item.get('taskTokens', {})

    # Find the human intervention token
    token_key = None
    task_token = None
    for key in ['brand_human_intervention', 'campaign_human_intervention']:
        if key in task_tokens:
            token_key = key
            task_token = task_tokens[key]
            break

    if not task_token:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'No pending human intervention found for this request',
                'currentStatus': item.get('status'),
            })
        }

    # Resume the Step Functions execution
    sfn.send_task_success(
        taskToken=task_token,
        output=json.dumps({
            'requestId': request_id,
            'resumedBy': 'human',
            'tokenKey': token_key,
        })
    )

    # Clean up the used token
    table.update_item(
        Key={'requestId': request_id},
        UpdateExpression='REMOVE taskTokens.#tk SET #s = :status, updatedAt = :now',
        ExpressionAttributeNames={
            '#tk': token_key,
            '#s': 'status',
        },
        ExpressionAttributeValues={
            ':status': f'RESUMED_FROM_{token_key.upper()}',
            ':now': _now(),
        }
    )

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'message': f'Workflow resumed for request {request_id}',
            'resumedFrom': token_key,
        })
    }


def _now():
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'
