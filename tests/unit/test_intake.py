# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Unit tests for the Intake Lambda."""
import json
import sys
import os
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws


@mock_aws
def test_intake_creates_item_and_starts_execution(aws_env):
    """Intake should write to DynamoDB and start a Step Functions execution."""
    # Set up mocked resources
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='test-registrations',
        KeySchema=[{'AttributeName': 'requestId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'requestId', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='test-registrations')

    # Mock Step Functions (moto doesn't fully support SFN start_execution)
    with patch('boto3.client') as mock_client:
        mock_sfn = MagicMock()
        mock_sfn.start_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-1:123456789012:execution:test:reg-123',
            'startDate': '2026-04-17T00:00:00Z',
        }

        def client_factory(service, **kwargs):
            if service == 'stepfunctions':
                return mock_sfn
            return boto3.client.__wrapped__(service, **kwargs) if hasattr(boto3.client, '__wrapped__') else boto3._get_default_session().client(service, **kwargs)

        # Import after env is set
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambda', 'intake'))
        import importlib
        import app as intake_app
        importlib.reload(intake_app)

        # Patch the sfn client on the module
        intake_app.sfn = mock_sfn

        event = {
            'body': json.dumps({
                'enableVetting': False,
                'brandFields': {'companyName': 'Test Co'},
                'campaignFields': {'campaignName': 'Test Campaign'},
                'attachments': {},
                'phoneConfig': {'messageType': 'TRANSACTIONAL'},
            })
        }

        result = intake_app.handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert 'requestId' in body
        assert body['message'] == 'Registration workflow started'

        # Verify DynamoDB item was created
        item = table.get_item(Key={'requestId': body['requestId']})['Item']
        assert item['status'] == 'SUBMITTED'
        assert item['brandFields']['companyName'] == 'Test Co'

        # Verify Step Functions was started
        mock_sfn.start_execution.assert_called_once()
        call_args = mock_sfn.start_execution.call_args
        assert 'reg-' in call_args.kwargs.get('name', call_args[1].get('name', ''))


@mock_aws
def test_intake_handles_empty_body(aws_env):
    """Intake should handle missing body gracefully."""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    dynamodb.create_table(
        TableName='test-registrations',
        KeySchema=[{'AttributeName': 'requestId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'requestId', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambda', 'intake'))
    import importlib
    import app as intake_app
    importlib.reload(intake_app)

    mock_sfn = MagicMock()
    mock_sfn.start_execution.return_value = {
        'executionArn': 'arn:aws:states:us-east-1:123456789012:execution:test:reg-123',
    }
    intake_app.sfn = mock_sfn

    event = {'body': '{}'}
    result = intake_app.handler(event, None)
    assert result['statusCode'] == 200
