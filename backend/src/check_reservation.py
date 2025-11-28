"""Check current reservation status handler"""
import os
import json
import logging
import boto3
import pytz
from typing import Any, Dict
from datetime import datetime, timedelta
from core import ConfigStore, ReservationClient

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)


def check_reservation_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """현재 예약 상태를 확인하는 Lambda 핸들러"""
    LOGGER.info("=== CHECK RESERVATION HANDLER STARTED ===")
    LOGGER.info("Received check reservation event: %s", event)
    
    try:
        LOGGER.info("Step 1: Parsing request body")
        # Parse body
        body = event.get("body")
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode()
        payload = json.loads(body) if body else {}
        LOGGER.info("Parsed payload: %s", payload)
        
        LOGGER.info("Step 2: Getting user ID")
        # Get user ID
        user_id = payload.get("userId") or os.environ.get("DEFAULT_USER_ID")
        if not user_id:
            LOGGER.warning("No userId provided")
            return _response(400, {"message": "userId is required"})
        LOGGER.info("User ID: %s", user_id)
        
        LOGGER.info("Step 3: Parsing target date")
        # Get target date (default: tomorrow in KST)
        target_date_str = payload.get("targetDate")
        if target_date_str:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        else:
            kst = pytz.timezone('Asia/Seoul')
            target_date = (datetime.now(kst) + timedelta(days=1)).date()
        LOGGER.info("Target date: %s", target_date)
        
        LOGGER.info("Step 4: Loading user preferences")
        # Load user preferences
        config_store = ConfigStore()
        # No master password needed with KMS
        preferences = config_store.get_user_preferences(user_id)
        LOGGER.info("User preferences loaded successfully")
        
        LOGGER.info("Step 5: Creating reservation client and logging in")
        # Check reservation status
        client = ReservationClient()
        
        # Login first
        login_result = client.login(
            preferences.user_id, 
            preferences.password, 
            preferences.raw_payload
        )
        
        if not login_result.success:
            LOGGER.warning("Login failed: %s", login_result.message)
            return _response(401, {
                "message": "Login failed",
                "error": login_result.message
            })
        LOGGER.info("Login successful")
        
        LOGGER.info("Step 6: Checking existing reservations")
        # Check existing reservations
        prvd_dt = target_date.strftime("%Y%m%d")
        reservations = client.check_existing_reservations(preferences.raw_payload, prvd_dt)
        LOGGER.info("Found %d reservations", len(reservations))
        
        result = {
            "userId": user_id,
            "targetDate": target_date.isoformat(),
            "hasReservation": len(reservations) > 0,
            "reservations": reservations
        }
        
        LOGGER.info("=== CHECK RESERVATION HANDLER COMPLETED SUCCESSFULLY ===")
        LOGGER.info("Check result: %s", result)
        return _response(200, result)
        
    except KeyError as e:
        LOGGER.error("=== CHECK RESERVATION HANDLER FAILED (User not found) ===")
        LOGGER.exception("User not found: %s", str(e))
        return _response(404, {"message": f"User not found: {str(e)}"})
    except Exception as error:
        LOGGER.error("=== CHECK RESERVATION HANDLER FAILED ===")
        LOGGER.exception("Error checking reservation: %s", str(error))
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

