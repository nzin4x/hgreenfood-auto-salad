"""HTTP client encapsulating the H.GreenFood reservation APIs."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests
import urllib3

from .models import ApiCallResult, LoginResult

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ReservationClient:
    MENU_CORNER_MAP = {
        "샌": "0005",
        "샐": "0006",
        "빵": "0007",
        "헬": "0009",
        "닭": "0010",
    }

    def __init__(
        self,
        base_url: str = "https://hcafe.hgreenfood.com",
        session: Optional[requests.Session] = None,
        timeout: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    def login(self, user_id: str, password: str, payload_defaults: Dict[str, str]) -> LoginResult:
        url = f"{self.base_url}/api/com/login.do"
        payload = {
            "userId": user_id,
            "userData": password,
            "osDvCd": payload_defaults.get("osDvCd", ""),
            "userCurrAppVer": payload_defaults.get("userCurrAppVer", "1.2.3"),
            "mobiPhTrmlId": payload_defaults.get("mobiPhTrmlId", ""),
        }
        response = self.session.post(url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=self.timeout, verify=False)
        json_body = self._safe_json(response)
        if response.status_code == 200 and json_body.get("errorCode") == 0:
            return LoginResult(True, "Login succeeded", json_body)
        message = json_body.get("errorMsg") if json_body else response.text
        return LoginResult(False, message or "Login failed", json_body)

    def reserve_menu(self, payload_template: Dict[str, Any], coner_dv_cd: str, prvd_dt: str, floor_name: Optional[str] = None) -> ApiCallResult:
        url = f"{self.base_url}/api/menu/reservation/insertReservationOrder.do"
        payload = dict(payload_template)
        
        # If payload_template is just the login session data, we add defaults.
        # If it's a fully constructed payload from ReservationService, we trust it.
        # We ensure critical fields are set.
        payload.update({
            "conerDvCd": coner_dv_cd,
            "prvdDt": prvd_dt,
        })
        
        # Add defaults if missing
        defaults = {
            "mealDvCd": "0002",
            "dlvrRsvDvCd": 1,
            "dsppUseYn": "Y",
            "ordQty": 1,
            "dlvrPlcSeq": 1,
        }
        for k, v in defaults.items():
            payload.setdefault(k, v)

        if floor_name:
            payload["floorNm"] = floor_name
        
        # Debug logging for payload
        import logging
        logger = logging.getLogger()
        logger.info(f"Full Reserve Payload: {json.dumps(payload, ensure_ascii=False)}")
        
        response = self.session.post(
            url,
            data=json.dumps(payload),
            headers=self._json_headers(),
            timeout=self.timeout,
            verify=False,
        )
        return self._wrap_response(response)

    def fetch_reserve_menu_list(self, prvd_dt: str, bizplc_cd: str) -> ApiCallResult:
        url = f"{self.base_url}/api/menu/reservation/selectReserveMenuList.do"
        payload = {
            "prvdDt": prvd_dt,
            "bizplcCd": bizplc_cd,
            "clcoMvicoYn": "Y",
            "reseFgCd": "3",
        }
        response = self.session.post(
            url,
            data=json.dumps(payload),
            headers=self._json_headers(),
            timeout=self.timeout,
            verify=False,
        )
        return self._wrap_response(response)

    def fetch_delivery_info_type_list(self, payload_template: Dict[str, Any], coner_dv_cd: str, prvd_dt: str) -> ApiCallResult:
        url = f"{self.base_url}/api/menu/reservation/selectDeliveryInfoTypeList.do"
        payload = {
            "conerDvCd": coner_dv_cd,
            "mealDvCd": "0002", # Assuming lunch
            "bizbrCd": payload_template.get("bizbrCd", "50856"), # Default or from payload
            "bizplcCd": payload_template.get("bizplcCd", "196274"),
            "prvdDt": prvd_dt,
        }
        response = self.session.post(
            url,
            data=json.dumps(payload),
            headers=self._json_headers(),
            timeout=self.timeout,
            verify=False,
        )
        return self._wrap_response(response)

    def fetch_reservations(self, prvd_dt: str, bizplc_cd: str) -> ApiCallResult:
        url = f"{self.base_url}/api/menu/reservation/selectMenuReservationList.do"
        payload = {
            "prvdDt": prvd_dt,
            "bizplcCd": bizplc_cd,
        }
        response = self.session.post(
            url,
            data=json.dumps(payload),
            headers=self._json_headers(),
            timeout=self.timeout,
            verify=False,
        )
        return self._wrap_response(response)

    def cancel_reservation(self, reservation_payload: Dict[str, str]) -> ApiCallResult:
        url = f"{self.base_url}/api/menu/reservation/updateMenuReservationCancel.do"
        response = self.session.post(
            url,
            data=json.dumps(reservation_payload),
            headers=self._json_headers(),
            timeout=self.timeout,
            verify=False,
        )
        return self._wrap_response(response)

    def check_existing_reservations(self, payload_defaults: Dict[str, Any], prvd_dt: str) -> list:
        """Check existing reservations for a given date"""
        url = f"{self.base_url}/api/menu/reservation/selectMenuReservationList.do"
        bizplc_cd = payload_defaults.get("bizplcCd", "196274")
        payload = {"prvdDt": prvd_dt, "bizplcCd": bizplc_cd}
        response = self.session.post(
            url,
            data=json.dumps(payload),
            headers=self._json_headers(),
            timeout=self.timeout,
            verify=False,
        )
        result = self._safe_json(response)
        if result.get("errorCode") == 0:
            # Response structure: dataSets.reserveList
            data_sets = result.get("dataSets", {})
            reservations = data_sets.get("reserveList", [])
            # Filter for the requested date and status 'A' (active)
            return [r for r in reservations if r.get("prvdDt") == prvd_dt and r.get("rsvStatCd") == "A"]
        return []

    def menu_code_for(self, initial: str) -> Optional[str]:
        return self.MENU_CORNER_MAP.get(initial.strip())

    def _wrap_response(self, response: requests.Response) -> ApiCallResult:
        payload = self._safe_json(response)
        if not payload:
            return ApiCallResult(False, None, response.text, {"statusCode": response.status_code, "body": response.text})
        success = payload.get("errorCode") == 0
        payload.setdefault("statusCode", response.status_code)
        return ApiCallResult(success, payload.get("errorCode"), payload.get("errorMsg"), payload)

    @staticmethod
    def _json_headers() -> Dict[str, str]:
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://hcafe.hgreenfood.com/ctf/menu/reservation/menuReservation.do",
            "Origin": "https://hcafe.hgreenfood.com",
        }

    @staticmethod
    def _safe_json(response: requests.Response) -> Dict[str, Any]:
        try:
            return response.json()
        except ValueError:
            return {}
