"""Immediate reservation handler"""
import os
import json
import logging
import boto3
from typing import Any, Dict
from datetime import datetime, timedelta
from core import ConfigStore, ReservationClient, HolidayService, ReservationService, SesNotifier

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)


def immediate_reservation_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """즉시 예약 실행"""
    LOGGER.info("=== IMMEDIATE RESERVATION HANDLER STARTED ===")
    LOGGER.info("Received immediate reservation request: %s", event)
    
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
        
        LOGGER.info("User ID: %s", user_id)
        
        LOGGER.info("Step 3: Retrieving master password from SSM")
        master_password = os.environ.get("MASTER_PASSWORD")
        if not master_password:
            ssm_param = os.environ.get("MASTER_PASSWORD_SSM_PARAM")
            if ssm_param:
                try:
                    LOGGER.info("Fetching master password from SSM: %s", ssm_param)
                    ssm_client = boto3.client("ssm")
                    response = ssm_client.get_parameter(Name=ssm_param, WithDecryption=True)
                    master_password = response["Parameter"]["Value"]
                    LOGGER.info("Successfully retrieved master password from SSM")
                except Exception as e:
                    LOGGER.error("Failed to fetch master password from SSM: %s", str(e), exc_info=True)
                    return _response(500, {"message": f"Failed to fetch master password: {str(e)}"})
        
        if not master_password:
            LOGGER.error("Master password not configured")
            return _response(500, {"message": "Master password not configured"})
        
        LOGGER.info("Step 4: Building reservation service")
        config_store = ConfigStore()
        
        holiday_endpoint = os.environ.get(
            "HOLIDAY_API_ENDPOINT",
            "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo",
        )
        holiday_service = HolidayService(endpoint=holiday_endpoint, config_store=config_store)
        
        notifier = None
        if os.environ.get("SES_SENDER_EMAIL"):
            notifier = SesNotifier()
        
        timezone = os.environ.get("DEFAULT_TIMEZONE", "Asia/Seoul")
        
        service = ReservationService(
            config_store=config_store,
            reservation_client=ReservationClient(),
            holiday_service=holiday_service,
            notifier=notifier,
            timezone=timezone,
        )
        
        LOGGER.info("Step 5: Making immediate reservation")
        # Make reservation for tomorrow
        result = service.run(user_id=user_id, master_password=master_password, service_date=None)
        
        LOGGER.info("=== IMMEDIATE RESERVATION HANDLER COMPLETED ===")
        return _response(200, {
            "success": result.success,
            "message": result.message,
            "targetDate": result.target_date.isoformat(),
            "attemptedMenus": result.attempted_menus,
            "details": result.details
        })
        
    except Exception as error:
        LOGGER.error("=== IMMEDIATE RESERVATION HANDLER FAILED ===")
        LOGGER.exception("Error making immediate reservation: %s", str(error))
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
