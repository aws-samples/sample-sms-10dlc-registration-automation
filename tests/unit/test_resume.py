# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Unit tests for the Resume Lambda."""
import json
import sys
import os
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws


def _setup_table_with_item(item):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='test-registrations',
        KeySchema=[{'AttributeName': 'requestId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'requestId', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='test-registrations')
    table.put_item(Item=item)
    return table


def _load_resume():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambda', 'resume'))
    import importlib
    import app as resume_app
    importlib.reload(resume_app)
    return resume_app


@mock_aws
def test_resume_sends_task_success(aws_env):
    """Should find the human intervention token and call SendTaskSuccess."""
    item = {
        'requestId': 'req-001',
        'status': 'BRAND_REQUIRES_UPDATES',
        'taskTokens': {'brand_human_intervention': 'token-human-123'},
    }
    _setup_table_with_item(item)

    app = _load_resume()
    mock_sfn = MagicMock()
    app.sfn = mock_sfn

    event = {'pathParameters': {'requestId': 'req-001'}}
    result = app.handler(event, None)

    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert 'resumed' in body['message'].lower()

    mock_sfn.send_task_success.assert_called_once()
    call_kwargs = mock_sfn.send_task_success.call_args.kwargs
    assert call_kwargs['taskToken'] == 'token-human-123'


@mock_aws
def test_resume_returns_404_for_unknown_request(aws_env):
    """Should return 404 if request ID doesn't exist."""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    dynamodb.create_table(
        TableName='test-registrations',
        KeySchema=[{'AttributeName': 'requestId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'requestId', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )

    app = _load_resume()
    event = {'pathParameters': {'requestId': 'nonexistent'}}
    result = app.handler(event, None)
    assert result['statusCode'] == 404


@mock_aws
def test_resume_returns_400_when_no_pending_intervention(aws_env):
    """Should return 400 if no human intervention token exists."""
    item = {
        'requestId': 'req-002',
        'status': 'BRAND_SUBMITTED',
        'taskTokens': {'brand': 'token-brand-normal'},
    }
    _setup_table_with_item(item)

    app = _load_resume()
    mock_sfn = MagicMock()
    app.sfn = mock_sfn

    event = {'pathParameters': {'requestId': 'req-002'}}
    result = app.handler(event, None)
    assert result['statusCode'] == 400
    mock_sfn.send_task_success.assert_not_called()


def test_resume_returns_400_for_missing_request_id(aws_env):
    """Should return 400 if requestId is missing from path."""
    app = _load_resume()
    event = {'pathParameters': {}}
    result = app.handler(event, None)
    assert result['statusCode'] == 400
