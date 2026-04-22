# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Quick script to check a DynamoDB item."""
import sys
import boto3

request_id = sys.argv[1] if len(sys.argv) > 1 else 'unknown'
region = sys.argv[2] if len(sys.argv) > 2 else 'us-west-2'
table_name = sys.argv[3] if len(sys.argv) > 3 else 'tendlc-reg-auto-registrations'

t = boto3.resource('dynamodb', region_name=region).Table(table_name)
item = t.get_item(Key={'requestId': request_id}).get('Item', {})

if not item:
    print(f'No item found for {request_id}')
    sys.exit(1)

print(f'requestId:  {item.get("requestId")}')
print(f'status:     {item.get("status")}')
print(f'brandRegId: {item.get("brandRegId")}')
print(f'campaignRegId: {item.get("campaignRegId")}')
print(f'taskTokens: {list(item.get("taskTokens", {}).keys())}')
print(f'updatedAt:  {item.get("updatedAt")}')
