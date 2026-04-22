# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Unit tests for the Event Router Lambda."""
import json
import sys
import os
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws


def _setup_table_with_item(item):
    """Create DynamoDB table and insert a test item."""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='test-registrations',
        KeySchema=[{'AttributeName': 'requestId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'requestId', 'AttributeType': 'S'},
            {'AttributeName': 'brandRegId', 'AttributeType': 'S'},
            {'AttributeName': 'campaignRegId', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'brand-reg-index',
                'KeySchema': [{'AttributeName': 'brandRegId', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
            {
                'IndexName': 'campaign-reg-index',
                'KeySchema': [{'AttributeName': 'campaignRegId', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='test-registrations')
    table.put_item(Item=item)
    return table


def _load_event_router():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambda', 'event_router'))
    import importlib
    import app as event_router_app
    importlib.reload(event_router_app)
    return event_router_app


def _make_event(reg_id, reg_type, status):
    return {
        'detail': {
            'registrationDetails': {
                'registrationId': reg_id,
                'registrationType': reg_type,
                'currentStatus': status,
            }
        }
    }


@mock_aws
def test_brand_complete_sends_task_success(aws_env):
    """When brand status is COMPLETE, should call SendTaskSuccess."""
    item = {
        'requestId': 'req-001',
        'brandRegId': 'reg-brand-001',
        'campaignRegId': '-',
        'status': 'BRAND_SUBMITTED',
        'taskTokens': {'brand': 'token-brand-abc'},
    }
    _setup_table_with_item(item)

    app = _load_event_router()
    mock_sfn = MagicMock()
    app.sfn = mock_sfn

    event = _make_event('reg-brand-001', 'US_TEN_DLC_BRAND_REGISTRATION', 'COMPLETE')
    result = app.handler(event, None)

    assert result['action'] == 'callback_sent'
    mock_sfn.send_task_success.assert_called_once()
    call_kwargs = mock_sfn.send_task_success.call_args.kwargs
    assert call_kwargs['taskToken'] == 'token-brand-abc'


@mock_aws
def test_brand_rejected_sends_task_failure(aws_env):
    """When brand status is REQUIRES_UPDATES, should call SendTaskFailure."""
    item = {
        'requestId': 'req-002',
        'brandRegId': 'reg-brand-002',
        'campaignRegId': '-',
        'status': 'BRAND_SUBMITTED',
        'taskTokens': {'brand': 'token-brand-def'},
    }
    _setup_table_with_item(item)

    app = _load_event_router()
    mock_sfn = MagicMock()
    app.sfn = mock_sfn

    event = _make_event('reg-brand-002', 'US_TEN_DLC_BRAND_REGISTRATION', 'REQUIRES_UPDATES')
    result = app.handler(event, None)

    assert result['action'] == 'callback_sent'
    mock_sfn.send_task_failure.assert_called_once()
    call_kwargs = mock_sfn.send_task_failure.call_args.kwargs
    assert call_kwargs['taskToken'] == 'token-brand-def'
    assert call_kwargs['error'] == 'REQUIRES_UPDATES'


@mock_aws
def test_ignored_status_does_nothing(aws_env):
    """CREATED, SUBMITTED, REVIEWING statuses should be ignored."""
    app = _load_event_router()
    mock_sfn = MagicMock()
    app.sfn = mock_sfn

    for status in ['CREATED', 'SUBMITTED', 'REVIEWING']:
        event = _make_event('reg-any', 'US_TEN_DLC_BRAND_REGISTRATION', status)
        result = app.handler(event, None)
        assert result['action'] == 'ignored'

    mock_sfn.send_task_success.assert_not_called()
    mock_sfn.send_task_failure.assert_not_called()


@mock_aws
def test_no_matching_request_returns_no_match(aws_env):
    """If no DynamoDB item matches the registration ID, return no_match."""
    # Create empty table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    dynamodb.create_table(
        TableName='test-registrations',
        KeySchema=[{'AttributeName': 'requestId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'requestId', 'AttributeType': 'S'},
            {'AttributeName': 'brandRegId', 'AttributeType': 'S'},
            {'AttributeName': 'campaignRegId', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'brand-reg-index',
                'KeySchema': [{'AttributeName': 'brandRegId', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
            {
                'IndexName': 'campaign-reg-index',
                'KeySchema': [{'AttributeName': 'campaignRegId', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    app = _load_event_router()
    event = _make_event('reg-nonexistent', 'US_TEN_DLC_BRAND_REGISTRATION', 'COMPLETE')
    result = app.handler(event, None)
    assert result['action'] == 'no_match'


@mock_aws
def test_human_intervention_token_takes_priority(aws_env):
    """If both 'brand' and 'brand_human_intervention' tokens exist, use the intervention one."""
    item = {
        'requestId': 'req-003',
        'brandRegId': 'reg-brand-003',
        'campaignRegId': '-',
        'status': 'BRAND_REJECTED',
        'taskTokens': {
            'brand_human_intervention': 'token-human-xyz',
        },
    }
    _setup_table_with_item(item)

    app = _load_event_router()
    mock_sfn = MagicMock()
    app.sfn = mock_sfn

    event = _make_event('reg-brand-003', 'US_TEN_DLC_BRAND_REGISTRATION', 'COMPLETE')
    result = app.handler(event, None)

    assert result['action'] == 'callback_sent'
    call_kwargs = mock_sfn.send_task_success.call_args.kwargs
    assert call_kwargs['taskToken'] == 'token-human-xyz'
