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
    holiday_service = HolidayService(endpoint=holiday_endpoint)

    notifier = None
    if os.environ.get("SES_SENDER_EMAIL"):
        notifier = SesNotifier()

    
    # Support both API Gateway (resource) and Function URL (rawPath)
    route = event.get("resource") or event.get("rawPath") or ""

    if route == "/register":
        from register_user import register_user_handler
        return register_user_handler(event, _context)
    
    # 예약 확인 이벤트
    if route == "/check-reservation":
        from check_reservation import check_reservation_handler
        return check_reservation_handler(event, _context)
    
    # 이메일 인증 코드 발송
    if route == "/auth/send-code":
        from auth_handler import send_verification_code_handler
        return send_verification_code_handler(event, _context)
    
    # 이메일 인증 코드 검증
    if route == "/auth/verify-code":
        from auth_handler import verify_code_handler
        return verify_code_handler(event, _context)
    
    # 디바이스 확인 (자동 로그인)
    if route == "/auth/check-device":
        from auth_handler import check_device_handler
        return check_device_handler(event, _context)
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

    results = []
    for user_id in user_ids or []:
        try:
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
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _resolve_master_password(payload: Optional[Dict[str, Any]] = None) -> str:
    if payload:
        candidate = payload.get("masterPassword") or payload.get("master_password")
        if candidate:
            return candidate
        detail = payload.get("detail")
        if isinstance(detail, dict):
            candidate = detail.get("masterPassword") or detail.get("master_password")
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