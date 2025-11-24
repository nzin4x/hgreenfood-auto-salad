"""Get user settings handler"""
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


def get_user_settings_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """사용자 설정 조회"""
    LOGGER.info("=== GET USER SETTINGS HANDLER STARTED ===")
    
    try:
        # Query parameter에서 userId 가져오기
        query_params = event.get("queryStringParameters") or {}
        user_id = query_params.get("userId")
        
        if not user_id:
            # Body에서도 시도
            body = event.get("body")
            if body:
                if event.get("isBase64Encoded"):
                    import base64
                    body = base64.b64decode(body).decode()
                payload = json.loads(body)
                user_id = payload.get("userId")
        
        if not user_id:
            return _response(400, {"message": "userId is required"})
        
        LOGGER.info("Fetching settings for user: %s", user_id)
        
        # Get master password from SSM
        master_password = os.environ.get("MASTER_PASSWORD")
        if not master_password:
            ssm_param = os.environ.get("MASTER_PASSWORD_SSM_PARAM")
            if ssm_param:
                ssm_client = boto3.client("ssm")
                response = ssm_client.get_parameter(Name=ssm_param, WithDecryption=True)
                master_password = response["Parameter"]["Value"]
        
        if not master_password:
            return _response(500, {"message": "Master password not configured"})
        
        # Get user preferences
        config_store = ConfigStore()
        preferences = config_store.get_user_preferences(user_id, master_password)
        
        return _response(200, {
            "userId": user_id,
            "menuSeq": preferences.menu_sequence,
            "floorNm": preferences.floor_name
        })
        
    except Exception as error:
        LOGGER.error("=== GET USER SETTINGS HANDLER FAILED ===")
        LOGGER.exception("Error getting settings: %s", str(error))
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
