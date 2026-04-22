# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""
Synthetic EventBridge Event Simulator

Instead of publishing to EventBridge (which blocks reserved 'aws.*' sources),
this simulator directly calls SendTaskSuccess/SendTaskFailure on the Step Functions
task tokens stored in DynamoDB. This exercises the same resume logic that the
Event Router Lambda uses, just bypassing the EventBridge â†’ Lambda hop.

For testing the Event Router Lambda itself, use the SAM local invoke fixtures
in tests/events/.

Usage:
    from event_simulator import EventSimulator

    sim = EventSimulator(region='us-east-1', table_name='my-table')
    sim.send_brand_approved(request_id='req-abc123')
    sim.send_campaign_rejected(request_id='req-xyz789')
"""
import json
import time

import boto3
from boto3.dynamodb.conditions import Key


class EventSimulator:
    """Drives Step Functions workflow by directly calling SendTaskSuccess/SendTaskFailure."""

    def __init__(self, region='us-east-1', table_name=None):
        self.sfn = boto3.client('stepfunctions', region_name=region)
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name) if table_name else None
        self.region = region

    def set_table(self, table_name):
        self.table = self.dynamodb.Table(table_name)

    def send_task_success(self, request_id, token_key, registration_id='synthetic'):
        """
        Look up the task token for the given key and call SendTaskSuccess.

        Args:
            request_id: The workflow request ID
            token_key: The task token key in DynamoDB (e.g., 'brand', 'campaign', 'vetting')
            registration_id: Synthetic registration ID for the output payload
        """
        task_token = self._get_token(request_id, token_key)
        self.sfn.send_task_success(
            taskToken=task_token,
            output=json.dumps({
                'registrationId': registration_id,
                'status': 'COMPLETE',
            })
        )
        print(f'  âœ“ SendTaskSuccess for "{token_key}" (request={request_id})')

    def send_task_failure(self, request_id, token_key, error='REQUIRES_UPDATES'):
        """
        Look up the task token for the given key and call SendTaskFailure.

        Args:
            request_id: The workflow request ID
            token_key: The task token key in DynamoDB
            error: The error code (e.g., REQUIRES_UPDATES, CLOSED)
        """
        task_token = self._get_token(request_id, token_key)
        self.sfn.send_task_failure(
            taskToken=task_token,
            error=error,
            cause=f'Synthetic test: {error}',
        )
        print(f'  âœ“ SendTaskFailure for "{token_key}" error={error} (request={request_id})')

    # â”€â”€ Convenience methods â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def send_brand_approved(self, request_id):
        return self.send_task_success(request_id, 'brand', 'synthetic-brand-reg')

    def send_brand_rejected(self, request_id):
        return self.send_task_failure(request_id, 'brand', 'REQUIRES_UPDATES')

    def send_vetting_approved(self, request_id):
        return self.send_task_success(request_id, 'vetting', 'synthetic-vetting-reg')

    def send_vetting_failed(self, request_id):
        return self.send_task_failure(request_id, 'vetting', 'REQUIRES_UPDATES')

    def send_campaign_approved(self, request_id):
        return self.send_task_success(request_id, 'campaign', 'synthetic-campaign-reg')

    def send_campaign_rejected(self, request_id):
        return self.send_task_failure(request_id, 'campaign', 'REQUIRES_UPDATES')

    # â”€â”€ Internal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _get_token(self, request_id, token_key, timeout=60, poll_interval=3):
        """Poll DynamoDB until the task token appears."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = self.table.get_item(Key={'requestId': request_id})
            item = resp.get('Item', {})
            tokens = item.get('taskTokens', {})
            if token_key in tokens:
                return tokens[token_key]
            time.sleep(poll_interval)
        raise TimeoutError(f'Task token "{token_key}" not found for {request_id} within {timeout}s')
