# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Unit tests for the Notification Lambda."""
import json
import sys
import os
from unittest.mock import MagicMock

import pytest


def _load_notification():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambda', 'notification'))
    import importlib
    import app as notification_app
    importlib.reload(notification_app)
    return notification_app


def test_brand_rejected_notification(aws_env):
    """Should publish SNS message for brand rejection."""
    app = _load_notification()
    mock_sns = MagicMock()
    app.sns = mock_sns

    event = {
        'Payload': {
            'requestId': 'req-001',
            'type': 'BRAND_REJECTED',
            'error': {'Error': 'REQUIRES_UPDATES', 'Cause': 'Missing info'},
        }
    }
    result = app.handler(event, None)

    assert result['notified'] is True
    assert result['type'] == 'BRAND_REJECTED'
    mock_sns.publish.assert_called_once()
    call_kwargs = mock_sns.publish.call_args.kwargs
    assert 'brand registration requires updates' in call_kwargs['Message'].lower()
    assert 'req-001' in call_kwargs['Message']


def test_registration_complete_notification(aws_env):
    """Should publish success notification."""
    app = _load_notification()
    mock_sns = MagicMock()
    app.sns = mock_sns

    event = {'Payload': {'requestId': 'req-002', 'type': 'REGISTRATION_COMPLETE'}}
    result = app.handler(event, None)

    assert result['notified'] is True
    call_kwargs = mock_sns.publish.call_args.kwargs
    assert 'complete' in call_kwargs['Message'].lower()


def test_all_notification_types_have_subjects(aws_env):
    """Every notification type should have a defined subject."""
    app = _load_notification()
    mock_sns = MagicMock()
    app.sns = mock_sns

    for ntype in ['BRAND_REJECTED', 'VETTING_FAILED', 'CAMPAIGN_REJECTED',
                   'REGISTRATION_COMPLETE', 'REGISTRATION_TIMED_OUT']:
        event = {'Payload': {'requestId': 'req-x', 'type': ntype, 'error': {}}}
        app.handler(event, None)
        call_kwargs = mock_sns.publish.call_args.kwargs
        assert len(call_kwargs['Subject']) > 0
        assert len(call_kwargs['Subject']) <= 100  # SNS subject limit
