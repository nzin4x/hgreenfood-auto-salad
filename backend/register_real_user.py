#!/usr/bin/env python3
"""Register real user data for testing"""
import sys
import os
import json

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set required environment variables
os.environ['CONFIG_TABLE_NAME'] = 'HGreenFoodAutoReserve'
os.environ['DYNAMODB_ENDPOINT_URL'] = 'http://localhost:8000'
os.environ['MASTER_PASSWORD'] = 'test-master-password'
os.environ['DEFAULT_USER_ID'] = 'nzin4x'
os.environ['DEFAULT_TIMEZONE'] = 'Asia/Seoul'

from register_user import register_user_handler

# Create event with real data
event = {
    "body": json.dumps({
        "userId": "nzin4x",
        "password": "",
        "pin": "1234",  # PIN은 사용자가 따로 설정하는 값이 있나요? 임시로 1234 사용
        "menuSeq": "샌,샐,빵",
        "floorNm": "5층"
    }),
    "isBase64Encoded": False,
    "httpMethod": "POST",
    "resource": "/register"
}

print("실제 사용자 데이터로 등록 중...")
print(f"userId: nzin4x")
print(f"menuSeq: 샌,샐,빵")
print(f"floorNm: 5층")
print("\n" + "="*60)

try:
    result = register_user_handler(event, None)
    print(f"Status Code: {result.get('statusCode')}")
    
    if result.get('body'):
        response_body = json.loads(result['body'])
        print(f"응답: {json.dumps(response_body, indent=2, ensure_ascii=False)}")
        
        if result.get('statusCode') == 200:
            print("\n✅ 사용자 등록 성공!")
            print("이제 예약 테스트를 진행할 수 있습니다.")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
