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
    
    if route == "/check-reservation":
        from check_reservation import check_reservation_handler
        return check_reservation_handler(event, _context)
    
    if route == "/auth/send-code":
        from auth_handler import send_verification_code_handler
        return send_verification_code_handler(event, _context)
    
    if route == "/auth/verify-code":
        from auth_handler import verify_code_handler
        return verify_code_handler(event, _context)
    
    if route == "/auth/check-device":
        from auth_handler import check_device_handler
        return check_device_handler(event, _context)
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

    if route == "/reservation/make-immediate":
        from immediate_reservation import immediate_reservation_handler
        return immediate_reservation_handler(event, _context)

    if route == "/admin/update-holidays":
        return update_holidays_handler(event, _context)

    if route == "/user/toggle-auto-reservation":
        from toggle_auto_reservation import toggle_auto_reservation_handler
        return toggle_auto_reservation_handler(event, _context)

    if route == "/user/delete-account":
        from delete_account import delete_account_handler
        return delete_account_handler(event, _context)

    if route == "/user/update-settings":
        from update_user_settings import update_user_settings_handler
        return update_user_settings_handler(event, _context)

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

        master_password = _resolve_master_password(payload)
        service_date = _parse_service_date(payload.get("serviceDate"))

        service = _build_service()
        result = service.run(user_id=user_id, master_password=master_password, service_date=service_date)

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
        LOGGER.exception("Unhandled error processing API request")
        return _response(500, {"message": "Internal server error", "error": str(error)})


def worker_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    LOGGER.info("Worker event triggered: %s", event.get("detail-type") or event.get("source"))
    try:
        master_password = _resolve_master_password(event)
    except ValueError as error:
        LOGGER.error("Master password unavailable: %s", error)
        raise

    service = _build_service()
    try:
        user_ids = service.config_store.list_users()
    except Exception as error:  # pylint: disable=broad-except
        LOGGER.exception("Failed to list users from configuration store")
        default_user = os.environ.get("DEFAULT_USER_ID")
        user_ids = [default_user] if default_user else []

    results = []
    for user_id in user_ids or []:
        try:
            preferences = service.config_store.get_user_preferences(user_id, master_password)
            if not preferences.auto_reservation_enabled:
                LOGGER.info("Auto-reservation disabled for user %s, skipping", user_id)
                results.append({
                    "userId": user_id,
                    "success": False,
                    "message": "Auto-reservation is disabled",
                    "skipped": True
                })
                continue
            
            outcome = service.run(user_id=user_id, master_password=master_password)
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
    body = event.get("body"

)
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


def _resolve_master_password(payload: Optional[Dict[str, Any]] = None) -> str:
    if payload:
        candidate = payload.get("masterPassword") or payload.get("master_password")
        if candidate:
            return candidate
        detail = payload.get("detail")
        if isinstance(detail, dict):
            candidate = detail.get("masterPassword") or payload.get("master_password")
            if candidate:
                return candidate

    env_password = os.environ.get("MASTER_PASSWORD")
    if env_password:
        return env_password

    ssm_param = os.environ.get("MASTER_PASSWORD_SSM_PARAM")
    if ssm_param:
        return _fetch_master_password_from_ssm(ssm_param)

    raise ValueError("Master password not supplied")


def _fetch_master_password_from_ssm(param_name: str) -> str:
    client = boto3.client("ssm")
    response = client.get_parameter(Name=param_name, WithDecryption=True)
    value = response["Parameter"]["Value"]
    if not value:
        raise ValueError(f"SSM parameter '{param_name}' is empty")
    return value