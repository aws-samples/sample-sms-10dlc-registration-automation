# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""
Shared helpers for integration tests.
"""
import json
import time

import boto3


def get_stack_outputs(stack_name, region='us-east-1'):
    """Fetch CloudFormation stack outputs as a dict."""
    cfn = boto3.client('cloudformation', region_name=region)
    resp = cfn.describe_stacks(StackName=stack_name)
    outputs = resp['Stacks'][0].get('Outputs', [])
    return {o['OutputKey']: o['OutputValue'] for o in outputs}


def get_dynamo_item(table_name, request_id, region='us-east-1'):
    """Fetch a registration item from DynamoDB."""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    resp = table.get_item(Key={'requestId': request_id})
    return resp.get('Item')


def wait_for_execution_status(sfn_client, execution_arn, target_statuses,
                               timeout=120, poll_interval=5):
    """
    Poll a Step Functions execution until it reaches one of the target statuses
    or a wait state (RUNNING with a specific state name).

    Returns (status, execution_detail).
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = sfn_client.describe_execution(executionArn=execution_arn)
        status = resp['status']
        if status in target_statuses:
            return status, resp
        if status == 'FAILED' or status == 'TIMED_OUT' or status == 'ABORTED':
            return status, resp
        time.sleep(poll_interval)

    raise TimeoutError(
        f'Execution {execution_arn} did not reach {target_statuses} within {timeout}s'
    )


def wait_for_task_token(table_name, request_id, token_key,
                        timeout=60, poll_interval=3, region='us-east-1'):
    """
    Poll DynamoDB until a task token appears for the given key.
    This means Step Functions has reached a waitForTaskToken state
    and the Lambda has stored the token.

    Returns the task token string.
    """
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    deadline = time.time() + timeout

    while time.time() < deadline:
        resp = table.get_item(Key={'requestId': request_id})
        item = resp.get('Item', {})
        tokens = item.get('taskTokens', {})
        if token_key in tokens:
            return tokens[token_key]
        time.sleep(poll_interval)

    raise TimeoutError(
        f'Task token "{token_key}" not found for request {request_id} within {timeout}s'
    )


def get_execution_history_events(sfn_client, execution_arn):
    """Get all history events for a Step Functions execution."""
    events = []
    paginator = sfn_client.get_paginator('get_execution_history')
    for page in paginator.paginate(executionArn=execution_arn):
        events.extend(page['events'])
    return events


def get_current_state(sfn_client, execution_arn):
    """
    Determine the current state of a running Step Functions execution
    by looking at the most recent TaskStateEntered event.
    """
    events = get_execution_history_events(sfn_client, execution_arn)
    for event in reversed(events):
        if event['type'] == 'TaskStateEntered':
            detail = event.get('stateEnteredEventDetails', {})
            return detail.get('name')
    return None


def submit_registration(api_endpoint, payload=None):
    """Submit a registration via the API Gateway endpoint."""
    import requests

    if payload is None:
        payload = build_test_payload()

    url = f'{api_endpoint}/api/submit'
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def resume_registration(api_endpoint, request_id):
    """Call the resume endpoint for human-in-the-loop."""
    import requests

    url = f'{api_endpoint}/api/resume/{request_id}'
    resp = requests.post(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_test_payload(enable_vetting=False):
    """Build a realistic test registration payload."""
    return {
        'enableVetting': enable_vetting,
        'brandFields': {
            'companyName': 'Test Company LLC',
            'taxIdIssuingCountry': 'US',
            'taxId': '123456789',
            'legalType': 'PRIVATE_PROFIT',
            'businessContactEmail': 'test@example.com',
            'address': '123 Test Street',
            'city': 'Seattle',
            'state': 'WA',
            'zipCode': '98101',
            'isoCountryCode': 'US',
            'dbaName': 'TestCo',
            'contactVertical': 'TECHNOLOGY',
            'website': 'https://example.com',
            'supportEmail': 'support@example.com',
            'supportPhoneNumber': '+12065551234',
        },
        'campaignFields': {
            'campaignName': 'Test Campaign',
            'campaignVertical': 'TECHNOLOGY',
            'termsAndConditionsLink': 'https://example.com/terms',
            'privacyPolicyLink': 'https://example.com/privacy',
            'optInWorkflow': 'Users opt in by texting START to our number.',
            'optInKeyword': 'START',
            'optInMessage': 'You are now opted in. Reply STOP to unsubscribe.',
            'helpMessage': 'Reply HELP for assistance. Contact support@example.com.',
            'stopMessage': 'You have been unsubscribed. No more messages is sent.',
            'numberCapabilities': 'SMS',
            'messageType': 'TRANSACTIONAL',
            'useCase': 'TWO_FACTOR_AUTHENTICATION',
            'subscriberOptIn': 'YES',
            'subscriberOptOut': 'YES',
            'subscriberHelp': 'YES',
            'directLending': 'NO',
            'embeddedLink': 'NO',
            'embeddedPhone': 'NO',
            'ageGated': 'NO',
            'messageSample1': 'Your verification code is {code}. Expires in 10 minutes.',
            'messageSample2': 'Your login code is {code}. Do not share this code.',
        },
        'attachments': {},
        'phoneConfig': {
            'messageType': 'TRANSACTIONAL',
            'capabilities': ['SMS'],
        },
    }
