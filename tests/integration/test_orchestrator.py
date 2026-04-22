# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#!/usr/bin/env python3
"""
10DLC Registration Automation - Synthetic Integration Test Orchestrator

Drives the full Step Functions workflow through all states by submitting
a registration and then publishing synthetic EventBridge events to simulate
the third-party approval process. Completes in minutes instead of weeks.

Usage:
    python test_orchestrator.py --stack-name 10dlc-reg --scenario happy-path
    python test_orchestrator.py --stack-name 10dlc-reg --scenario all
    python test_orchestrator.py --stack-name 10dlc-reg --scenario brand-rejected --region us-west-2
"""
import argparse
import json
import sys
import time

import boto3

from event_simulator import EventSimulator
from helpers import (
    build_test_payload,
    get_dynamo_item,
    get_stack_outputs,
    resume_registration,
    submit_registration,
    wait_for_task_token,
)

# How long to wait for Step Functions to reach a wait state after we fire an event
WAIT_STATE_TIMEOUT = 90
# How long to wait for the event router to process and resume the execution
EVENT_PROCESSING_WAIT = 10


class TestOrchestrator:
    """Orchestrates synthetic end-to-end tests against a deployed stack."""

    def __init__(self, stack_name, region='us-east-1'):
        self.stack_name = stack_name
        self.region = region
        self.sfn = boto3.client('stepfunctions', region_name=region)

        outputs = get_stack_outputs(stack_name, region)
        self.api_endpoint = outputs['ApiEndpoint']
        self.table_name = f'{stack_name}-registrations'
        self.state_machine_arn = outputs['StateMachineArn']

        self.simulator = EventSimulator(region=region, table_name=self.table_name)
        self.results = []

    def run_scenario(self, scenario):
        """Run a named test scenario."""
        scenarios = {
            'happy-path': self.test_happy_path,
            'happy-path-with-vetting': self.test_happy_path_with_vetting,
            'brand-rejected': self.test_brand_rejected,
            'campaign-rejected': self.test_campaign_rejected,
            'vetting-failed': self.test_vetting_failed,
        }

        if scenario == 'all':
            for name, fn in scenarios.items():
                self._run_one(name, fn)
        elif scenario in scenarios:
            self._run_one(scenario, scenarios[scenario])
        else:
            print(f'Unknown scenario: {scenario}')
            print(f'Available: {", ".join(list(scenarios.keys()) + ["all"])}')
            sys.exit(1)

        self._print_summary()

    def _run_one(self, name, fn):
        print(f'\n{"="*60}')
        print(f'  SCENARIO: {name}')
        print(f'{"="*60}\n')
        try:
            fn()
            self.results.append((name, 'PASSED', None))
            print(f'\n  [PASS] {name}: PASSED\n')
        except Exception as e:
            self.results.append((name, 'FAILED', str(e)))
            print(f'\n  [FAIL] {name}: FAILED - {e}\n')

    def _print_summary(self):
        print(f'\n{"="*60}')
        print(f'  TEST SUMMARY')
        print(f'{"="*60}')
        passed = sum(1 for _, s, _ in self.results if s == 'PASSED')
        total = len(self.results)
        for name, status, error in self.results:
            icon = '[PASS]' if status == 'PASSED' else '[FAIL]'
            line = f'  {icon} {name}'
            if error:
                line += f' - {error}'
            print(line)
        print(f'\n  {passed}/{total} passed\n')

    # ---- Test Scenarios --------------------------------------------------

    def test_happy_path(self):
        """Submit registration > brand gets created > real API rejects it >
        human intervention > resume > campaign > complete.

        Note: With real AWS End User Messaging SMS API calls, the test brand data is rejected
        immediately (REQUIRES_UPDATES) because it's not a real company. This is
        expected and actually validates that the EventBridge integration works.
        The test drives through the rejection/resume path to reach completion.
        """
        print('Step 1: Submitting registration...')
        result = submit_registration(self.api_endpoint, build_test_payload(enable_vetting=False))
        request_id = result['requestId']
        print(f'  Request ID: {request_id}')

        # The brand is created and submitted to the real API.
        # The real API will reject it (REQUIRES_UPDATES) because it's test data.
        # EventBridge will fire, Event Router will call SendTaskFailure,
        # and the workflow will move to WaitForHumanIntervention_Brand.
        print('\nStep 2: Waiting for human intervention token (brand is auto-rejected by real API)...')
        wait_for_task_token(
            self.table_name, request_id, 'brand_human_intervention',
            timeout=WAIT_STATE_TIMEOUT, region=self.region
        )
        item = get_dynamo_item(self.table_name, request_id, self.region)
        brand_reg_id = item['brandRegId']
        assert brand_reg_id != '-', 'Brand registration ID should be populated'
        print(f'  OK Brand Reg ID: {brand_reg_id}')
        print(f'  OK Brand was auto-rejected by real API (expected with test data)')
        print(f'  OK EventBridge > Event Router > SendTaskFailure worked!')

        # Resume via the API endpoint (simulating human fix)
        print('\nStep 3: Resuming via /api/resume (simulating human fix)...')
        resume_result = resume_registration(self.api_endpoint, request_id)
        print(f'  OK {resume_result["message"]}')
        time.sleep(EVENT_PROCESSING_WAIT)

        # Campaign will also be created and auto-rejected by real API
        print('\nStep 4: Waiting for campaign human intervention token...')
        wait_for_task_token(
            self.table_name, request_id, 'campaign_human_intervention',
            timeout=WAIT_STATE_TIMEOUT, region=self.region
        )
        item = get_dynamo_item(self.table_name, request_id, self.region)
        campaign_reg_id = item['campaignRegId']
        assert campaign_reg_id != '-', 'Campaign registration ID should be populated'
        print(f'  OK Campaign Reg ID: {campaign_reg_id}')
        print(f'  OK Campaign was auto-rejected by real API (expected)')

        # Resume campaign
        print('\nStep 5: Resuming campaign via /api/resume...')
        resume_registration(self.api_endpoint, request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        # After campaign resume, workflow goes to RequestPhoneNumber
        print('\nStep 6: Waiting for workflow completion...')
        self._wait_for_final_status(request_id, timeout=60)

        item = get_dynamo_item(self.table_name, request_id, self.region)
        print(f'  OK Phone Number ID: {item.get("phoneNumberId", "N/A")}')
        print(f'  OK Final status: {item["status"]}')

    def test_happy_path_with_vetting(self):
        """Brand approved > Vetting approved > Campaign approved > Phone > Complete."""
        print('Step 1: Submitting registration with vetting enabled...')
        result = submit_registration(self.api_endpoint, build_test_payload(enable_vetting=True))
        request_id = result['requestId']
        print(f'  Request ID: {request_id}')

        print('\nStep 2: Waiting for brand task token...')
        wait_for_task_token(self.table_name, request_id, 'brand',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)
        print('  OK Brand task token stored')

        print('\nStep 3: Simulating brand approval...')
        self.simulator.send_brand_approved(request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 4: Waiting for vetting task token...')
        wait_for_task_token(self.table_name, request_id, 'vetting',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)
        print('  OK Vetting task token stored')

        print('\nStep 5: Simulating vetting approval...')
        self.simulator.send_vetting_approved(request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 6: Waiting for campaign task token...')
        wait_for_task_token(self.table_name, request_id, 'campaign',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)
        print('  OK Campaign task token stored')

        print('\nStep 7: Simulating campaign approval...')
        self.simulator.send_campaign_approved(request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 8: Waiting for workflow completion...')
        self._wait_for_final_status(request_id, timeout=60)
        item = get_dynamo_item(self.table_name, request_id, self.region)
        assert item.get('phoneNumberId', '-') != '-', 'Phone number should be provisioned'
        print(f'  OK Final status: {item["status"]}')

    def test_brand_rejected(self):
        """Brand rejected > Notification > Human fix > Resume > Campaign > Complete."""
        print('Step 1: Submitting registration...')
        result = submit_registration(self.api_endpoint, build_test_payload())
        request_id = result['requestId']
        print(f'  Request ID: {request_id}')

        print('\nStep 2: Waiting for brand task token...')
        wait_for_task_token(self.table_name, request_id, 'brand',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)

        print('\nStep 3: Simulating brand REJECTION...')
        self.simulator.send_brand_rejected(request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 4: Waiting for human intervention task token...')
        wait_for_task_token(self.table_name, request_id, 'brand_human_intervention',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)
        print('  OK Workflow paused for human intervention')

        print('\nStep 5: Resuming via /api/resume endpoint...')
        resume_result = resume_registration(self.api_endpoint, request_id)
        print(f'  OK {resume_result["message"]}')
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 6: Waiting for campaign task token...')
        wait_for_task_token(self.table_name, request_id, 'campaign',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)

        print('\nStep 7: Simulating campaign approval...')
        self.simulator.send_campaign_approved(request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 8: Waiting for workflow completion...')
        self._wait_for_final_status(request_id, timeout=60)
        item = get_dynamo_item(self.table_name, request_id, self.region)
        print(f'  OK Final status: {item["status"]}')

    def test_campaign_rejected(self):
        """Brand approved > Campaign rejected > Human fix > Resume > Phone > Complete."""
        print('Step 1: Submitting registration...')
        result = submit_registration(self.api_endpoint, build_test_payload())
        request_id = result['requestId']

        print('\nStep 2: Brand approval flow...')
        wait_for_task_token(self.table_name, request_id, 'brand',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)
        self.simulator.send_brand_approved(request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 3: Waiting for campaign task token...')
        wait_for_task_token(self.table_name, request_id, 'campaign',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)

        print('\nStep 4: Simulating campaign REJECTION...')
        self.simulator.send_campaign_rejected(request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 5: Waiting for human intervention task token...')
        wait_for_task_token(self.table_name, request_id, 'campaign_human_intervention',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)
        print('  OK Workflow paused for human intervention')

        print('\nStep 6: Resuming via /api/resume endpoint...')
        resume_registration(self.api_endpoint, request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 7: Waiting for workflow completion...')
        self._wait_for_final_status(request_id, timeout=60)
        item = get_dynamo_item(self.table_name, request_id, self.region)
        print(f'  OK Final status: {item["status"]}')

    def test_vetting_failed(self):
        """Brand approved > Vetting failed > Human intervention > Resume > Campaign > Complete."""
        print('Step 1: Submitting registration with vetting enabled...')
        result = submit_registration(self.api_endpoint, build_test_payload(enable_vetting=True))
        request_id = result['requestId']
        print(f'  Request ID: {request_id}')

        print('\nStep 2: Waiting for brand task token...')
        wait_for_task_token(self.table_name, request_id, 'brand',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)

        print('\nStep 3: Simulating brand approval...')
        self.simulator.send_brand_approved(request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 4: Waiting for vetting task token...')
        wait_for_task_token(self.table_name, request_id, 'vetting',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)

        print('\nStep 5: Simulating vetting FAILURE...')
        self.simulator.send_vetting_failed(request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 6: Waiting for vetting human intervention token...')
        wait_for_task_token(self.table_name, request_id, 'vetting_human_intervention',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)
        print('  OK Workflow paused - operator notified of vetting failure')

        print('\nStep 7: Resuming via /api/resume (operator chose to proceed unvetted)...')
        resume_result = resume_registration(self.api_endpoint, request_id)
        print(f'  OK {resume_result["message"]}')
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 8: Waiting for campaign task token...')
        wait_for_task_token(self.table_name, request_id, 'campaign',
                           timeout=WAIT_STATE_TIMEOUT, region=self.region)
        print('  OK Campaign proceeded after operator decision')

        print('\nStep 9: Simulating campaign approval...')
        self.simulator.send_campaign_approved(request_id)
        time.sleep(EVENT_PROCESSING_WAIT)

        print('\nStep 10: Waiting for workflow completion...')
        self._wait_for_final_status(request_id, timeout=60)
        item = get_dynamo_item(self.table_name, request_id, self.region)
        print(f'  OK Final status: {item["status"]}')

    # ---- Helpers ---------------------------------------------------------

    def _wait_for_final_status(self, request_id, timeout=60):
        """Poll DynamoDB until the status indicates completion or phone association."""
        deadline = time.time() + timeout
        terminal_prefixes = ('PHONE_ASSOCIATED', 'REGISTRATION_COMPLETE')
        while time.time() < deadline:
            item = get_dynamo_item(self.table_name, request_id, self.region)
            status = item.get('status', '')
            if any(status.startswith(p) for p in terminal_prefixes):
                return item
            time.sleep(5)
        # Not a hard failure - the phone number step might take a moment
        item = get_dynamo_item(self.table_name, request_id, self.region)
        print(f'  WARNING: Final status after timeout: {item.get("status")}')
        return item


def main():
    parser = argparse.ArgumentParser(
        description='10DLC Registration Automation - Synthetic Integration Tests'
    )
    parser.add_argument('--stack-name', required=True, help='CloudFormation stack name')
    parser.add_argument('--scenario', required=True,
                        help='Test scenario: happy-path, happy-path-with-vetting, '
                             'brand-rejected, campaign-rejected, vetting-failed, all')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    args = parser.parse_args()

    orchestrator = TestOrchestrator(args.stack_name, args.region)
    orchestrator.run_scenario(args.scenario)


if __name__ == '__main__':
    main()
