#!/usr/bin/env python3
"""Test reservation check with real user data"""
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

from check_reservation import check_reservation_handler

# Calculate tomorrow's date
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

# Create test event
event = {
    "body": json.dumps({
        "userId": "nzin4x",
        "targetDate": tomorrow
    }),
    "isBase64Encoded": False,
    "httpMethod": "POST",
    "resource": "/check-reservation"
}

print("="*60)
print("예약 상태 확인 테스트")
print("="*60)
print(f"사용자: nzin4x")
print(f"확인 날짜: {tomorrow}")
print("\n실제 API 호출 중...")
print("="*60)

try:
    result = check_reservation_handler(event, None)
    print(f"\nStatus Code: {result.get('statusCode')}")
    
    if result.get('body'):
        response_body = json.loads(result['body'])
        print(f"\n응답:")
        print(json.dumps(response_body, indent=2, ensure_ascii=False))
        
        if response_body.get('hasReservation'):
            print("\n✅ 예약이 존재합니다!")
            print(f"예약 개수: {len(response_body.get('reservations', []))}")
        else:
            print("\n❌ 예약이 없습니다.")
            
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
