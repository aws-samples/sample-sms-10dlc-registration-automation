# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""
Shared fixtures for unit tests.
Sets up mocked AWS services and environment variables.
"""
import json
import os
import pytest
import boto3
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    """Set environment variables that all Lambdas expect."""
    monkeypatch.setenv('REGISTRATIONS_TABLE', 'test-registrations')
    monkeypatch.setenv('UPLOAD_BUCKET', 'test-uploads')
    monkeypatch.setenv('STATE_MACHINE_ARN', 'arn:aws:states:us-east-1:123456789012:stateMachine:test-workflow')
    monkeypatch.setenv('NOTIFICATION_TOPIC_ARN', 'arn:aws:sns:us-east-1:123456789012:test-notifications')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')


@pytest.fixture
def dynamodb_table():
    """Create a mocked DynamoDB table matching the SAM template schema."""
    with mock_aws():
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
        yield table


@pytest.fixture
def s3_bucket():
    """Create a mocked S3 bucket."""
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-uploads')
        yield s3


@pytest.fixture
def sns_topic():
    """Create a mocked SNS topic."""
    with mock_aws():
        sns = boto3.client('sns', region_name='us-east-1')
        resp = sns.create_topic(Name='test-notifications')
        yield sns, resp['TopicArn']


@pytest.fixture
def sample_registration_item():
    """A DynamoDB item representing a registration in progress."""
    return {
        'requestId': 'test-request-001',
        'status': 'BRAND_SUBMITTED',
        'createdAt': '2026-04-17T00:00:00Z',
        'updatedAt': '2026-04-17T00:00:00Z',
        'enableVetting': False,
        'brandFields': {
            'companyName': 'Test Company LLC',
            'taxIdIssuingCountry': 'US',
            'taxId': '12-3456789',
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
            'messageType': 'TRANSACTIONAL',
            'useCase': 'TWO_FACTOR_AUTHENTICATION',
            'messageSample1': 'Your code is {code}.',
        },
        'attachments': {},
        'phoneConfig': {'messageType': 'TRANSACTIONAL', 'capabilities': ['SMS']},
        'brandRegId': '-',
        'campaignRegId': '-',
        'vettingRegId': '-',
        'phoneNumberId': '-',
        'attachmentIds': {},
        'taskTokens': {},
    }
