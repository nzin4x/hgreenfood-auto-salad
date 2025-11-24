"""Email authentication and device fingerprint management"""
import os
import json
import logging
import base64
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import ClientError

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)

# DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('CONFIG_TABLE_NAME', 'HGreenFoodAutoReserve')
table = dynamodb.Table(table_name)

# SES client
ses = boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'ap-northeast-2'))


def send_verification_code_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """이메일 인증 코드 발송"""
    LOGGER.info("Received send verification code event")
    
    try:
        body = _parse_body(event)
        email = body.get("email")
        
        if not email:
            return _response(400, {"message": "Email is required"})
        
        # 6자리 인증 코드 생성
        verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # DynamoDB에 인증 코드 저장 (TTL 10분)
        expiry_time = int((datetime.utcnow() + timedelta(minutes=10)).timestamp())
        
        try:
            table.put_item(Item={
                "PK": f"VERIFY#{email}",
                "SK": "CODE",
                "code": verification_code,
                "email": email,
                "expiresAt": expiry_time,
                "createdAt": datetime.utcnow().isoformat()
            })
        except ClientError as e:
            LOGGER.error(f"DynamoDB error: {e}")
            return _response(500, {"message": "Failed to store verification code"})
        
        # SES로 이메일 발송
        sender = os.environ.get('SES_SENDER_EMAIL', 'no-reply@example.com')
        subject = "HGreenFood 예약 서비스 인증 코드"
        body_text = f"""
안녕하세요,

HGreenFood 자동 예약 서비스 인증 코드입니다.

인증 코드: {verification_code}

이 코드는 10분간 유효합니다.

감사합니다.
"""
        
        try:
            ses.send_email(
                Source=sender,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {'Text': {'Data': body_text, 'Charset': 'UTF-8'}}
                }
            )
        except ClientError as e:
            LOGGER.error(f"SES error: {e}")
            return _response(500, {"message": "Failed to send email"})
        
        LOGGER.info(f"Verification code sent to {email}")
        return _response(200, {"message": "Verification code sent", "email": email})
        
    except Exception as error:
        LOGGER.exception("Error sending verification code")
        return _response(500, {"message": str(error)})


def verify_code_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """이메일 인증 코드 검증 및 디바이스 등록"""
    LOGGER.info("Received verify code event")
    
    try:
        body = _parse_body(event)
        email = body.get("email")
        code = body.get("code")
        device_fingerprint = body.get("deviceFingerprint")
        
        if not email or not code:
            return _response(400, {"message": "Email and code are required"})
        
        # DynamoDB에서 인증 코드 조회
        try:
            response = table.get_item(Key={"PK": f"VERIFY#{email}", "SK": "CODE"})
            item = response.get("Item")
            
            if not item:
                return _response(401, {"message": "Invalid or expired verification code"})
            
            # 코드 검증
            if item.get("code") != code:
                return _response(401, {"message": "Invalid verification code"})
            
            # 만료 시간 확인
            if int(item.get("expiresAt", 0)) < int(datetime.utcnow().timestamp()):
                return _response(401, {"message": "Verification code expired"})
            
            # 인증 성공 - 코드 삭제
            table.delete_item(Key={"PK": f"VERIFY#{email}", "SK": "CODE"})
            
            # 기존 사용자 확인
            user_response = table.scan(
                FilterExpression="email = :email AND SK = :sk",
                ExpressionAttributeValues={":email": email, ":sk": "PROFILE"}
            )
            
            existing_user = user_response.get("Items", [])
            
            # 세션 토큰 생성 (디바이스 지문 기반)
            session_token = _generate_session_token(email, device_fingerprint)
            
            result = {
                "message": "Verification successful",
                "email": email,
                "sessionToken": session_token,
                "hasAccount": len(existing_user) > 0
            }
            
            if existing_user:
                user = existing_user[0]
                result["userId"] = user.get("userId")
                
                # 디바이스 등록
                if device_fingerprint:
                    _register_device(user.get("userId"), device_fingerprint)
            
            return _response(200, result)
            
        except ClientError as e:
            LOGGER.error(f"DynamoDB error: {e}")
            return _response(500, {"message": "Database error"})
        
    except Exception as error:
        LOGGER.exception("Error verifying code")
        return _response(500, {"message": str(error)})


def check_device_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """디바이스 지문 확인 및 자동 로그인"""
    LOGGER.info("Received check device event")
    
    try:
        body = _parse_body(event)
        device_fingerprint = body.get("deviceFingerprint")
        
        if not device_fingerprint:
            return _response(400, {"message": "Device fingerprint is required"})
        
        # 모든 사용자의 디바이스 목록에서 검색
        response = table.scan(
            FilterExpression="attribute_exists(devices)"
        )
        
        for item in response.get("Items", []):
            devices = item.get("devices", [])
            for device in devices:
                if device.get("fingerprint") == device_fingerprint:
                    # 디바이스 발견 - 자동 로그인
                    user_id = item.get("userId")
                    session_token = _generate_session_token(item.get("email"), device_fingerprint)
                    
                    # 마지막 접속 시간 업데이트
                    _update_device_access(user_id, device_fingerprint)
                    
                    return _response(200, {
                        "authenticated": True,
                        "userId": user_id,
                        "email": item.get("email"),
                        "sessionToken": session_token
                    })
        
        # 디바이스 미등록
        return _response(200, {"authenticated": False})
        
    except Exception as error:
        LOGGER.exception("Error checking device")
        return _response(500, {"message": str(error)})


def _register_device(user_id: str, device_fingerprint: str) -> None:
    """사용자에게 디바이스 등록"""
    try:
        # 먼저 기존 devices 조회
        response = table.get_item(Key={"PK": f"USER#{user_id}", "SK": "PROFILE"})
        item = response.get("Item")
        
        if not item:
            LOGGER.warning(f"User {user_id} not found for device registration")
            return
        
        devices = item.get("devices", [])
        
        # 이미 등록된 디바이스인지 확인
        for device in devices:
            if device.get("fingerprint") == device_fingerprint:
                LOGGER.info(f"Device already registered for user {user_id}, updating lastAccessAt")
                device["lastAccessAt"] = datetime.utcnow().isoformat()
                table.update_item(
                    Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
                    UpdateExpression="SET devices = :devices",
                    ExpressionAttributeValues={":devices": devices}
                )
                return
        
        # 새 디바이스 정보 생성
        device_info = {
            "fingerprint": device_fingerprint,
            "registeredAt": datetime.utcnow().isoformat(),
            "lastAccessAt": datetime.utcnow().isoformat()
        }
        
        # 기존 devices 배열에 추가
        devices.append(device_info)
        table.update_item(
            Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
            UpdateExpression="SET devices = :devices",
            ExpressionAttributeValues={":devices": devices}
        )
        LOGGER.info(f"New device registered for user {user_id}")
    except ClientError as e:
        LOGGER.error(f"Failed to register device: {e}")



def _update_device_access(user_id: str, device_fingerprint: str) -> None:
    """디바이스 마지막 접속 시간 업데이트"""
    try:
        response = table.get_item(Key={"PK": f"USER#{user_id}", "SK": "PROFILE"})
        item = response.get("Item")
        
        if not item:
            return
        
        devices = item.get("devices", [])
        updated = False
        
        for device in devices:
            if device.get("fingerprint") == device_fingerprint:
                device["lastAccessAt"] = datetime.utcnow().isoformat()
                updated = True
                break
        
        if updated:
            table.update_item(
                Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
                UpdateExpression="SET devices = :devices",
                ExpressionAttributeValues={":devices": devices}
            )
    except ClientError as e:
        LOGGER.error(f"Failed to update device access: {e}")


def _generate_session_token(email: str, device_fingerprint: Optional[str]) -> str:
    """세션 토큰 생성"""
    data = f"{email}:{device_fingerprint}:{secrets.token_hex(16)}"
    return hashlib.sha256(data.encode()).hexdigest()


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }
