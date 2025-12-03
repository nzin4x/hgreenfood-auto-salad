"""Lambda entrypoints for API Gateway and scheduled worker."""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime, date
from typing import Any, Dict, Optional

import boto3

from core import (
    ConfigStore,
    HolidayService,
    ReservationClient,
    ReservationService,
    SesNotifier,
)

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)

_SERVICE: Optional[ReservationService] = None


def _build_service() -> ReservationService:
    global _SERVICE
    if _SERVICE:
        return _SERVICE

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

    _SERVICE = ReservationService(
        config_store=config_store,
        reservation_client=ReservationClient(),
        holiday_service=holiday_service,
        notifier=notifier,
        timezone=timezone,
    )
    return _SERVICE


def api_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    LOGGER.info("Received API event: %s", event.get("routeKey") or event.get("httpMethod") or event.get("rawPath"))
    
    route = event.get("resource") or event.get("rawPath") or ""

    if route == "/register":
        from register_user import register_user_handler
        return register_user_handler(event, _context)

    if route == "/register/status":
        from get_registration_status import get_registration_status_handler
        return get_registration_status_handler(event, _context)
    
    if route == "/check-reservation":
        from check_reservation import check_reservation_handler
        return check_reservation_handler(event, _context)

    if route == "/reservations":
        from list_reservations import list_reservations_handler
        return list_reservations_handler(event, _context)
    
    if route == "/auth/send-code":
        from auth_handler import send_verification_code_handler
        return send_verification_code_handler(event, _context)
    
    if route == "/auth/verify-code":
        from auth_handler import verify_code_handler
        return verify_code_handler(event, _context)
    
    if route == "/auth/check-device":
        from auth_handler import check_device_handler
        return check_device_handler(event, _context)
    
    if route == "/auth/logout":
        from logout_handler import logout_handler
        return logout_handler(event, _context)
    
    if route == "/user/toggle-auto-reservation":
        from toggle_auto_reservation import toggle_auto_reservation_handler
        return toggle_auto_reservation_handler(event, _context)

    if route == "/user/delete-account":
        from delete_account import delete_account_handler
        return delete_account_handler(event, _context)

    if route == "/user/get-settings":
        from get_user_settings import get_user_settings_handler
        return get_user_settings_handler(event, _context)

    if route == "/user/update-settings":
        from update_user_settings import update_user_settings_handler
        return update_user_settings_handler(event, _context)
    
    if route == "/user/update-exclusion-dates":
        from update_exclusion_dates import update_exclusion_dates_handler
        return update_exclusion_dates_handler(event, _context)

    if route == "/reservation/make-immediate":
        from immediate_reservation import immediate_reservation_handler
        return immediate_reservation_handler(event, _context)

    if route == "/admin/update-holidays":
        return update_holidays_handler(event, _context)

    try:
        payload = _parse_body(event)
        user_id = payload.get("userId") or os.environ.get("DEFAULT_USER_ID")
        if not user_id:
            return _response(400, {"message": "userId is required"})

        service_date = _parse_service_date(payload.get("serviceDate"))

        service = _build_service()
        result = service.run(user_id=user_id, service_date=service_date)

        return _response(
            200,
            {
                "success": result.success,
                "message": result.message,
                "targetDate": result.target_date.isoformat(),
                "attemptedMenus": result.attempted_menus,
                "details": result.details,
            },
        )
    except ValueError as error:
        LOGGER.warning("Client error: %s", error)
        return _response(400, {"message": str(error)})
    except Exception as error:  # pylint: disable=broad-except
        LOGGER.exception("API error: %s", error)
        return _response(500, {"message": str(error)})


def worker_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """Worker Lambda handler for scheduled reservation tasks"""
    LOGGER.info("=== WORKER HANDLER STARTED ===")
    LOGGER.info("Received worker event: %s", event)
    
    try:
        service = _build_service()
        
        # Get all users from DynamoDB instead of using DEFAULT_USER_ID
        LOGGER.info("Fetching all user profiles from DynamoDB...")
        user_profiles = service.config_store.get_all_user_profiles()
        LOGGER.info(f"Found {len(user_profiles)} total user profiles")
        
        # Extract user IDs and log them
        user_ids = []
        for profile in user_profiles:
            user_id = profile.get("userId")
            if user_id:
                user_ids.append(user_id)
                # Log user info for processing order visibility
                auto_enabled = profile.get("autoReservationEnabled", True)
                menu_seq = profile.get("menuSeq", "N/A")
                floor_nm = profile.get("floorNm", "N/A")
                LOGGER.info(f"User found: {user_id}, AutoReserve: {auto_enabled}, MenuSeq: {menu_seq}, Floor: {floor_nm}")
        
        LOGGER.info(f"Processing {len(user_ids)} users in order: {user_ids}")
        
        results = []
        for idx, user_id in enumerate(user_ids, 1):
            LOGGER.info(f"[{idx}/{len(user_ids)}] Processing user: {user_id}")
            try:
                preferences = service.config_store.get_user_preferences(user_id)
                if not preferences.auto_reservation_enabled:
                    LOGGER.info("Auto-reservation disabled for user %s, skipping", user_id)
                    results.append({
                        "userId": user_id,
                        "success": False,
                        "message": "Auto-reservation is disabled",
                        "skipped": True
                    })
                    continue
                
                outcome = service.run(user_id=user_id)
                results.append(
                    {
                        "userId": user_id,
                        "success": outcome.success,
                        "message": outcome.message,
                        "targetDate": outcome.target_date.isoformat(),
                    }
                )
            except Exception as error:  # pylint: disable=broad-except
                LOGGER.exception("Reservation attempt failed for %s", user_id)
                results.append({"userId": user_id, "success": False, "message": str(error)})

        LOGGER.info("Worker completed: %s", results)
        return {"results": results}
    except Exception as error:  # pylint: disable=broad-except
        LOGGER.exception("Worker handler failed: %s", error)
        return {"results": [{"success": False, "message": str(error)}]}


def update_holidays_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    LOGGER.info("Received holiday update request")
    try:
        payload = _parse_body(event)
        today = date.today()
        year = int(payload.get("year", today.year))
        month = int(payload.get("month", today.month))
        
        api_key = os.environ.get("HOLIDAY_API_KEY")
        if not api_key:
             return _response(500, {"message": "Holiday API key not configured"})

        service = _build_service()
        holidays = service.holiday_service.fetch_and_save_holidays(year, month, api_key)
        
        return _response(200, {
            "message": "Holidays updated successfully",
            "year": year,
            "month": month,
            "holidays": list(holidays)
        })
    except Exception as error:
        LOGGER.exception("Failed to update holidays")
        return _response(500, {"message": str(error)})


def holiday_scheduler_handler(event: Dict[str, Any], _context: Any) -> None:
    LOGGER.info("Holiday scheduler triggered")
    today = date.today()
    if today.month == 12:
        next_year = today.year + 1
        next_month = 1
    else:
        next_year = today.year
        next_month = today.month + 1
        
    api_key = os.environ.get("HOLIDAY_API_KEY")
    if not api_key:
        LOGGER.error("Holiday API key not configured")
        return

    service = _build_service()
    try:
        holidays = service.holiday_service.fetch_and_save_holidays(next_year, next_month, api_key)
        LOGGER.info(f"Successfully updated holidays for {next_year}-{next_month}: {holidays}")
    except Exception as error:
        LOGGER.exception(f"Failed to update holidays for {next_year}-{next_month}")


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise ValueError("Request body must be valid JSON") from error


def _parse_service_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
        return parsed.date()
    except ValueError as error:
        raise ValueError("serviceDate must be formatted as YYYY-MM-DD") from error


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


