"""Toggle auto-reservation handler"""
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


def toggle_auto_reservation_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """자동 예약 활성화/비활성화 토글"""
    LOGGER.info("=== TOGGLE AUTO-RESERVATION HANDLER STARTED ===")
    LOGGER.info("Received toggle request: %s", event)
    
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
        
        if "enabled" not in payload:
            LOGGER.warning("No enabled field provided")
            return _response(400, {"message": "enabled field is required"})
        
        enabled = payload.get("enabled")
        if not isinstance(enabled, bool):
            LOGGER.warning("Invalid enabled value type: %s", type(enabled))
            return _response(400, {"message": "enabled must be a boolean"})
        
        LOGGER.info("User ID: %s, Enabled: %s", user_id, enabled)
        
        LOGGER.info("Step 3: Updating auto-reservation status in DynamoDB")
        config_store = ConfigStore()
        config_store.update_auto_reservation_status(user_id, enabled)
        
        LOGGER.info("=== TOGGLE AUTO-RESERVATION HANDLER COMPLETED SUCCESSFULLY ===")
        return _response(200, {
            "message": "Auto-reservation status updated successfully",
            "userId": user_id,
            "autoReservationEnabled": enabled
        })
        
    except Exception as error:
        LOGGER.error("=== TOGGLE AUTO-RESERVATION HANDLER FAILED ===")
        LOGGER.exception("Error toggling auto-reservation: %s", str(error))
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
