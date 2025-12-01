"""Update user settings handler"""
import os
import json
import logging
import boto3
from typing import Any, Dict
from core import ConfigStore

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)


def update_user_settings_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """사용자 설정 업데이트 (예약 순서, 층 등)"""
    LOGGER.info("=== UPDATE USER SETTINGS HANDLER STARTED ===")
    LOGGER.info("Received update settings request: %s", event)
    
    try:
        LOGGER.info("Step 1: Parsing request body")
        body = event.get("body")
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode()
        payload = json.loads(body) if body else {}
        LOGGER.info("Parsed payload: %s", payload)
        
        LOGGER.info("Step 2: Validating required fields")
        user_id = payload.get("userId")
        if not user_id:
            LOGGER.warning("No userId provided")
            return _response(400, {"message": "userId is required"})
        
        # Optional fields to update
        menu_sequence = payload.get("menuSeq")  # e.g., ["백반A", "백반B"]
        floor_name = payload.get("floorNm")
        hg_user_id = payload.get("hgUserId")
        hg_user_pw = payload.get("hgUserPw")
        
        if not menu_sequence and not floor_name and not hg_user_id and not hg_user_pw:
            return _response(400, {"message": "At least one field to update is required"})
        
        LOGGER.info("User ID: %s, MenuSeq: %s, FloorNm: %s, HgUserId: %s, HgUserPw: %s", 
                    user_id, menu_sequence, floor_name, 
                    hg_user_id if hg_user_id else "not provided",
                    "***" if hg_user_pw else "not provided")
        
        LOGGER.info("Step 3: Updating user settings in DynamoDB")
        config_store = ConfigStore()
        config_store.update_user_settings(user_id, menu_sequence, floor_name, hg_user_id, hg_user_pw)
        
        LOGGER.info("=== UPDATE USER SETTINGS HANDLER COMPLETED SUCCESSFULLY ===")
        return _response(200, {
            "message": "Settings updated successfully",
            "userId": user_id
        })
        
    except Exception as error:
        LOGGER.error("=== UPDATE USER SETTINGS HANDLER FAILED ===")
        LOGGER.exception("Error updating settings: %s", str(error))
        return _response(500, {"message": str(error)})


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
