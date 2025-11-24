#!/usr/bin/env python3
"""
AWS DynamoDB에 사용자 등록 스크립트
로컬 DynamoDB의 사용자를 AWS로 마이그레이션하거나 새로운 사용자를 등록
"""
import boto3
import sys
import json
from typing import Dict, Any

def migrate_user_to_aws(local_item: Dict[str, Any], region: str = "ap-northeast-2") -> None:
    """로컬 DynamoDB 아이템을 AWS DynamoDB로 마이그레이션"""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table('HGreenFoodAutoReserve')
    
    try:
        table.put_item(Item=local_item)
        print(f"✅ 사용자 {local_item.get('userId')} 마이그레이션 완료")
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        raise

def scan_local_users() -> list:
    """로컬 DynamoDB에서 모든 사용자 스캔"""
    dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')
    table = dynamodb.Table('HGreenFoodAutoReserve')
    
    response = table.scan()
    return response.get('Items', [])

def main():
    if len(sys.argv) < 2:
        print("Usage: python migrate_to_aws.py [scan|migrate-all]")
        print("  scan: 로컬 DynamoDB 사용자 목록 조회")
        print("  migrate-all: 모든 로컬 사용자를 AWS로 마이그레이션")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "scan":
        users = scan_local_users()
        print(f"\n로컬 DynamoDB 사용자 수: {len(users)}")
        for item in users:
            if item.get('SK') == 'PROFILE':
                print(f"  - {item.get('userId')}: {item.get('email', 'N/A')}")
    
    elif command == "migrate-all":
        users = scan_local_users()
        print(f"\n{len(users)}개 아이템을 AWS로 마이그레이션합니다...")
        
        for item in users:
            if item.get('SK') == 'PROFILE':
                try:
                    migrate_user_to_aws(item)
                except Exception as e:
                    print(f"⚠️  {item.get('userId')} 마이그레이션 실패: {e}")
                    continue
        
        print("\n✅ 마이그레이션 완료!")
    
    else:
        print(f"❌ 알 수 없는 명령어: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
