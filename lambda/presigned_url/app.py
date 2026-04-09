"""
Presigned URL Lambda — generates time-limited S3 PUT URLs
for direct browser-to-S3 file uploads.
"""
import json
import os
import uuid

import boto3

s3 = boto3.client('s3')
BUCKET = os.environ['UPLOAD_BUCKET']
ALLOWED_TYPES = {'image/png', 'image/jpeg', 'application/pdf'}
MAX_SIZE = 500 * 1024  # 500KB per EUM SMS attachment limit
URL_EXPIRY = 600  # 10 minutes


def handler(event, context):
    body = json.loads(event.get('body', '{}'))

    content_type = body.get('contentType', '')
    field_name = body.get('fieldName', '')
    request_id = body.get('requestId', str(uuid.uuid4()))

    if content_type not in ALLOWED_TYPES:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': f'Invalid file type: {content_type}. Must be PNG, JPEG, or PDF.'
            })
        }

    if not field_name:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'fieldName is required'})
        }

    # Generate a scoped S3 key
    ext = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'application/pdf': '.pdf',
    }.get(content_type, '')
    s3_key = f'uploads/{request_id}/{field_name}{ext}'

    # Generate presigned PUT URL
    url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': BUCKET,
            'Key': s3_key,
            'ContentType': content_type,
        },
        ExpiresIn=URL_EXPIRY,
    )

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'uploadUrl': url,
            's3Key': s3_key,
            'bucket': BUCKET,
            'expiresIn': URL_EXPIRY,
        })
    }
