"""Logout handler - removes device registration"""
import os
import json
import logging
import base64
from typing import Any, Dict
import boto3
from botocore.exceptions import ClientError

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('CONFIG_TABLE_NAME', 'HGreenFoodAutoReserve')
table = dynamodb.Table(table_name)


def logout_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """로그아웃 - 디바이스 등록 해제"""
    LOGGER.info("Received logout event")
    
    try:
        body = _parse_body(event)
        user_id = body.get("userId")
        device_fingerprint = body.get("deviceFingerprint")
        
        if not user_id or not device_fingerprint:
            return _response(400, {"message": "userId and deviceFingerprint are required"})
        
        # 사용자 프로필에서 디바이스 제거
        response = table.get_item(Key={"PK": f"USER#{user_id}", "SK": "PROFILE"})
        item = response.get("Item")
        
        if not item:
            return _response(404, {"message": "User not found"})
        
        devices = item.get("devices", [])
        original_count = len(devices)
        
        # 해당 디바이스 제거
        devices = [d for d in devices if d.get("fingerprint") != device_fingerprint]
        
        if len(devices) < original_count:
            # 디바이스 목록 업데이트
            table.update_item(
                Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
                UpdateExpression="SET devices = :devices",
                ExpressionAttributeValues={":devices": devices}
            )
            LOGGER.info(f"Device removed for user {user_id}")
            return _response(200, {"message": "Logout successful", "deviceRemoved": True})
        else:
            LOGGER.info(f"Device not found for user {user_id}")
            return _response(200, {"message": "Logout successful", "deviceRemoved": False})
        
    except ClientError as e:
        LOGGER.error(f"DynamoDB error: {e}")
        return _response(500, {"message": "Database error"})
    except Exception as error:
        LOGGER.exception("Error during logout")
        return _response(500, {"message": str(error)})


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
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }
