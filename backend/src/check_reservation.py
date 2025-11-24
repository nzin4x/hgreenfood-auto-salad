"""Check current reservation status handler"""
import os
import json
import logging
from typing import Any, Dict
from datetime import datetime, timedelta
from core import ConfigStore, ReservationClient

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)


def check_reservation_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """현재 예약 상태를 확인하는 Lambda 핸들러"""
    LOGGER.info("Received check reservation event: %s", event)
    
    try:
        # Parse body
        body = event.get("body")
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode()
        payload = json.loads(body) if body else {}
        
        # Get user ID
        user_id = payload.get("userId") or os.environ.get("DEFAULT_USER_ID")
        if not user_id:
            return _response(400, {"message": "userId is required"})
        
        # Get master password
        master_password = os.environ.get("MASTER_PASSWORD")
        if not master_password:
            return _response(500, {"message": "Master password not configured"})
        
        # Get target date (default: tomorrow)
        target_date_str = payload.get("targetDate")
        if target_date_str:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        else:
            target_date = (datetime.now() + timedelta(days=1)).date()
        
        # Load user preferences
        config_store = ConfigStore()
        preferences = config_store.get_user_preferences(user_id, master_password)
        
        # Check reservation status
        client = ReservationClient()
        
        # Login first
        login_result = client.login(
            preferences.user_id, 
            preferences.password, 
            preferences.raw_payload
        )
        
        if not login_result.success:
            return _response(401, {
                "message": "Login failed",
                "error": login_result.message
            })
        
        # Check existing reservations
        prvd_dt = target_date.strftime("%Y%m%d")
        reservations = client.check_existing_reservations(preferences.raw_payload, prvd_dt)
        
        result = {
            "userId": user_id,
            "targetDate": target_date.isoformat(),
            "hasReservation": len(reservations) > 0,
            "reservations": reservations
        }
        
        LOGGER.info("Check result: %s", result)
        return _response(200, result)
        
    except KeyError as e:
        LOGGER.exception("User not found")
        return _response(404, {"message": f"User not found: {str(e)}"})
    except Exception as error:
        LOGGER.exception("Error checking reservation")
        return _response(500, {"message": str(error)})


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
