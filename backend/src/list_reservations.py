"""Return raw reservation list from H.GreenFood without filtering."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

import pytz

from core import ConfigStore, ReservationClient

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)


def list_reservations_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    LOGGER.info("=== LIST RESERVATIONS HANDLER STARTED ===")
    LOGGER.info("Received list reservations request: %s", event)

    try:
        body = event.get("body")
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode()
        payload = json.loads(body) if body else {}

        user_id = payload.get("userId") or os.environ.get("DEFAULT_USER_ID")
        if not user_id:
            return _response(400, {"message": "userId is required"})

        # Determine 'today' by configured timezone for stable results
        tz = pytz.timezone(os.environ.get("DEFAULT_TIMEZONE", "Asia/Seoul"))
        today = datetime.now(tz).date()
        prvd_dt = today.strftime("%Y%m%d")

        config_store = ConfigStore()
        preferences = config_store.get_user_preferences(user_id)

        client = ReservationClient()
        login_result = client.login(preferences.user_id, preferences.password, preferences.raw_payload)
        if not login_result.success:
            return _response(401, {"message": "Login failed", "error": login_result.message})

        bizplc_cd = preferences.raw_payload.get("bizplcCd", "196274")
        api_result = client.fetch_reservations(prvd_dt, bizplc_cd)
        if not api_result.success:
            return _response(502, {"message": api_result.message or "Failed to fetch reservations", "raw": api_result.payload})

        data_sets = api_result.raw.get("dataSets", {}) if isinstance(api_result.raw, dict) else {}
        reserve_list = data_sets.get("reserveList", [])

        return _response(200, {"reserveList": reserve_list, "sourceDate": prvd_dt})

    except Exception as error:  # pylint: disable=broad-except
        LOGGER.exception("Error listing reservations: %s", str(error))
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
