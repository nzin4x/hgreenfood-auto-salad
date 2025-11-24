#!/usr/bin/env python3
"""Test reservation API with real user data"""
import sys
import os
import json
from datetime import datetime, timedelta

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set required environment variables
os.environ['CONFIG_TABLE_NAME'] = 'HGreenFoodAutoReserve'
os.environ['DYNAMODB_ENDPOINT_URL'] = 'http://localhost:8000'
os.environ['MASTER_PASSWORD'] = 'test-master-password'
os.environ['DEFAULT_USER_ID'] = 'nzin4x'
os.environ['DEFAULT_TIMEZONE'] = 'Asia/Seoul'

from app import api_handler

# Calculate service date (tomorrow or specified date)
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

# Create test event
event = {
    "body": json.dumps({
        "userId": "nzin4x",
        "serviceDate": tomorrow
    }),
    "isBase64Encoded": False,
    "httpMethod": "POST",
    "resource": "/"  # Default reservation endpoint
}

print("="*60)
print("예약 API 테스트")
print("="*60)
print(f"사용자: nzin4x")
print(f"예약 날짜: {tomorrow}")
print(f"메뉴 우선순위: 샌,샐,빵")
print(f"배달 장소: 5층")
print("\n실제 예약 시도 중...")
print("="*60)

try:
    result = api_handler(event, None)
    print(f"\nStatus Code: {result.get('statusCode')}")
    
    if result.get('body'):
        response_body = json.loads(result['body'])
        print(f"\n응답:")
        print(json.dumps(response_body, indent=2, ensure_ascii=False))
        
        if response_body.get('success'):
            print("\n✅ 예약 성공!")
        else:
            print(f"\n❌ 예약 실패: {response_body.get('message')}")
            
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
