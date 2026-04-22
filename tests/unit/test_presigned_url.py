# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Unit tests for the Presigned URL Lambda."""
import json
import sys
import os
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws


def _load_presigned():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambda', 'presigned_url'))
    import importlib
    import app as presigned_app
    importlib.reload(presigned_app)
    return presigned_app


@mock_aws
def test_generates_presigned_url_for_png(aws_env):
    """Should return a presigned URL for valid PNG upload."""
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-uploads')

    app = _load_presigned()

    event = {
        'body': json.dumps({
            'contentType': 'image/png',
            'fieldName': 'optInScreenshot',
            'requestId': 'req-001',
        })
    }
    result = app.handler(event, None)

    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert 'uploadUrl' in body
    assert body['s3Key'] == 'uploads/req-001/optInScreenshot.png'
    assert body['expiresIn'] == 600


@mock_aws
def test_rejects_invalid_content_type(aws_env):
    """Should reject non-PNG/JPEG/PDF content types."""
    app = _load_presigned()

    event = {
        'body': json.dumps({
            'contentType': 'text/html',
            'fieldName': 'optInScreenshot',
        })
    }
    result = app.handler(event, None)

    assert result['statusCode'] == 400
    body = json.loads(result['body'])
    assert 'Invalid file type' in body['error']


@mock_aws
def test_rejects_missing_field_name(aws_env):
    """Should reject requests without fieldName."""
    app = _load_presigned()

    event = {
        'body': json.dumps({
            'contentType': 'image/png',
        })
    }
    result = app.handler(event, None)

    assert result['statusCode'] == 400
    body = json.loads(result['body'])
    assert 'fieldName is required' in body['error']


@mock_aws
def test_supports_pdf_and_jpeg(aws_env):
    """Should accept PDF and JPEG content types."""
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-uploads')

    app = _load_presigned()

    for ctype, ext in [('application/pdf', '.pdf'), ('image/jpeg', '.jpg')]:
        event = {
            'body': json.dumps({
                'contentType': ctype,
                'fieldName': 'testFile',
                'requestId': 'req-002',
            })
        }
        result = app.handler(event, None)
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['s3Key'].endswith(ext)
