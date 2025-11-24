"""Delete user account handler"""
import os
import json
import logging
from typing import Any, Dict
from core import ConfigStore

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)


def delete_account_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """사용자 계정 삭제 (탈퇴)"""
    LOGGER.info("=== DELETE ACCOUNT HANDLER STARTED ===")
    LOGGER.info("Received delete account request: %s", event)
    
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
        
        confirm = payload.get("confirm")
        if not confirm:
            LOGGER.warning("No confirmation provided")
            return _response(400, {"message": "Confirmation required"})
        
        LOGGER.info("User ID: %s, Confirm: %s", user_id, confirm)
        
        LOGGER.info("Step 3: Deleting user profile from DynamoDB")
        config_store = ConfigStore()
        config_store.delete_profile(user_id)
        
        LOGGER.info("=== DELETE ACCOUNT HANDLER COMPLETED SUCCESSFULLY ===")
        return _response(200, {
            "message": "Account deleted successfully",
            "userId": user_id
        })
        
    except Exception as error:
        LOGGER.error("=== DELETE ACCOUNT HANDLER FAILED ===")
        LOGGER.exception("Error deleting account: %s", str(error))
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
