#!/usr/bin/env python3
"""Test register_user handler locally without SAM"""
import sys
import os
import json

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set required environment variables
os.environ['CONFIG_TABLE_NAME'] = 'HGreenFoodAutoReserve'
os.environ['DYNAMODB_ENDPOINT_URL'] = 'http://localhost:8000'
os.environ['MASTER_PASSWORD'] = 'test-master-password'
os.environ['DEFAULT_USER_ID'] = 'sample-user'
os.environ['DEFAULT_TIMEZONE'] = 'Asia/Seoul'

from register_user import register_user_handler

# Create test event
event = {
    "body": json.dumps({
        "userId": "testuser1",
        "password": "testpass123",
        "pin": "1234",
        "menuSeq": "샐러드,빵",
        "floorNm": "5층"
    }),
    "isBase64Encoded": False,
    "httpMethod": "POST",
    "resource": "/register"
}

# Call handler
print("Testing user registration...")
print(f"Event: {json.dumps(event, indent=2, ensure_ascii=False)}")
print("\n" + "="*60)

try:
    result = register_user_handler(event, None)
    print(f"Status Code: {result.get('statusCode')}")
    print(f"Response: {result.get('body')}")
    
    # Parse response body
    if result.get('body'):
        response_body = json.loads(result['body'])
        print(f"\nParsed Response: {json.dumps(response_body, indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
