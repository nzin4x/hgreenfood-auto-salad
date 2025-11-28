"""High level orchestration for the reservation workflow."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Optional

import pytz

from .config_store import ConfigStore
from .holiday_service import HolidayService
from .models import ReservationAttempt
from .reservation_client import ReservationClient
from .ses_notifier import SesNotifier


class ReservationService:
    def __init__(
        self,
        config_store: ConfigStore,
        reservation_client: ReservationClient,
        holiday_service: Optional[HolidayService] = None,
        notifier: Optional[SesNotifier] = None,
        timezone: str = "Asia/Seoul",
    ) -> None:
        self.config_store = config_store
        self.reservation_client = reservation_client
        self.holiday_service = holiday_service
        self.notifier = notifier
        self.timezone = timezone

    def run(self, user_id: str, service_date: Optional[date] = None) -> ReservationAttempt:
        preferences = self.config_store.get_user_preferences(user_id)
        tz_name = preferences.timezone or self.timezone
        tz = pytz.timezone(tz_name)
        holiday_api_key = os.environ.get("HOLIDAY_API_KEY")
        target_date = service_date or self._next_service_date(tz, holiday_api_key)

        if self.holiday_service and holiday_api_key:
            if self.holiday_service.is_holiday(target_date, holiday_api_key):
                attempt = ReservationAttempt(False, "Skipped due to public holiday", target_date, [])
                self._notify(preferences, attempt, success=False)
                return attempt
        
        # Check user exclusion dates
        target_date_str = target_date.isoformat()
        if target_date_str in preferences.exclusion_dates:
            attempt = ReservationAttempt(False, f"Skipped due to user exclusion date: {target_date_str}", target_date, [])
            self._notify(preferences, attempt, success=False)
            return attempt

        login_result = self.reservation_client.login(preferences.user_id, preferences.password, preferences.raw_payload)
        if not login_result.success:
            attempt = ReservationAttempt(False, login_result.message, target_date, [], {"login": login_result.response_payload})
            self._notify(preferences, attempt, success=False)
            return attempt

        # 기존 예약 확인
        target_prvd_dt = target_date.strftime("%Y%m%d")
        existing_reservations = self.reservation_client.check_existing_reservations(preferences.raw_payload, target_prvd_dt)
        if existing_reservations:
            # 활성 예약이 있으면 스킵
            reservation_details = existing_reservations[0]
            attempt = ReservationAttempt(
                True,
                f"Reservation already exists: {reservation_details.get('dispNm', 'Unknown')}",
                target_date,
                [],
                {"existingReservation": reservation_details}
            )
            self._notify(preferences, attempt, success=True)
            return attempt

        attempted = []
        last_error = None

        # 메뉴 목록 조회
        bizplc_cd = preferences.raw_payload.get("bizplcCd", "196274")
        menu_list_result = self.reservation_client.fetch_reserve_menu_list(target_prvd_dt, bizplc_cd)
        available_menus = []
        if menu_list_result.success:
            data_sets = menu_list_result.raw.get("dataSets", {})
            available_menus = data_sets.get("reserveList", [])
        else:
            import logging
            LOGGER = logging.getLogger()
            LOGGER.warning(f"Failed to fetch menu list: {menu_list_result.error_message}")

        attempted = []
        last_error = None

        for menu_initial in preferences.menu_sequence:
            coner_dv_cd = self.reservation_client.menu_code_for(menu_initial)
            if not coner_dv_cd:
                continue
            
            # 1. Find matching menu item from available_menus (fetched earlier)
            menu_item = next((m for m in available_menus if m.get("conerDvCd") == coner_dv_cd), None)
            if not menu_item:
                import logging
                LOGGER = logging.getLogger()
                LOGGER.warning(f"Menu {menu_initial} (code {coner_dv_cd}) not found in available menus")
                continue

            # 2. Fetch Delivery Info Type List to get floor details
            delivery_info_result = self.reservation_client.fetch_delivery_info_type_list(preferences.raw_payload, coner_dv_cd, target_prvd_dt)
            delivery_info_item = None
            if delivery_info_result.success:
                delivery_list = delivery_info_result.raw.get("dataSets", {}).get("deliveryInfoTypeList", [])
                # Find item matching user's floor name
                target_floor = preferences.floor_name
                delivery_info_item = next((d for d in delivery_list if d.get("floorNm") == target_floor), None)
                
                if not delivery_info_item:
                    import logging
                    LOGGER = logging.getLogger()
                    LOGGER.warning(f"Floor {target_floor} not found in delivery info list. Available: {[d.get('floorNm') for d in delivery_list]}")
                    if not target_floor and delivery_list:
                         delivery_info_item = delivery_list[0]
            else:
                import logging
                LOGGER = logging.getLogger()
                LOGGER.warning(f"Failed to fetch delivery info: {delivery_info_result.error_message}")

            if not delivery_info_item:
                 import logging
                 LOGGER = logging.getLogger()
                 LOGGER.warning("Could not determine delivery info (floor details). Skipping.")
                 continue

            # 3. Build Payload
            reservation_payload = dict(preferences.raw_payload)
            reservation_payload.update({
                "bizplcCd": menu_item.get("bizplcCd"),
                "conerDvCd": coner_dv_cd,
                "mealDvCd": menu_item.get("mealDvCd", "0002"),
                "prvdDt": target_prvd_dt,
                "rownum": delivery_info_item.get("rownum"),
                "dlvrPlcFloorNo": delivery_info_item.get("dlvrPlcFloorNo"),
                "alphabetSeq": delivery_info_item.get("alphabetSeq"),
                "dlvrPlcFloorSeq": delivery_info_item.get("dlvrPlcFloorSeq"),
                "remainDeliQty": delivery_info_item.get("remainDeliQty"),
                "dlvrPlcNm": delivery_info_item.get("dlvrPlcNm"),
                "ordQty": 1,
                "totalCount": delivery_info_item.get("totalCount"),
                "floorNm": delivery_info_item.get("floorNm"), # Use the one from API
                "maxDelvQty": delivery_info_item.get("maxDelvQty"),
                "dlvrPlcSeq": delivery_info_item.get("dlvrPlcSeq"),
                "dlvrRsvDvCd": 1,
                "dsppUseYn": "Y"
            })
            
            attempted.append(menu_initial)
            import logging
            logger = logging.getLogger()
            logger.info(f"Reserving menu {menu_initial} for user {preferences.user_id} with floor: {preferences.floor_name}")
            
            result = self.reservation_client.reserve_menu(reservation_payload, coner_dv_cd, target_prvd_dt, preferences.floor_name)
            if result.success:
                attempt = ReservationAttempt(True, f"Reserved for menu {menu_initial}", target_date, attempted.copy(), result.raw)
                self._notify(preferences, attempt, success=True)
                return attempt
            last_error = result
            if result.error_message == "동일날짜에 이미 등록된 예약이 존재합니다.":
                attempt = ReservationAttempt(True, "Reservation already exists", target_date, attempted.copy(), result.raw)
                self._notify(preferences, attempt, success=True)
                return attempt

        message = last_error.error_message if last_error else "Reservation attempt failed"
        details = last_error.raw if last_error else {}
        attempt = ReservationAttempt(False, message or "Reservation attempt failed", target_date, attempted, details)
        self._notify(preferences, attempt, success=False)
        return attempt

    def _next_service_date(self, tz, holiday_api_key: Optional[str]) -> date:
        candidate = (datetime.now(tz) + timedelta(days=1)).date()
        while True:
            if candidate.weekday() < 5:
                if not holiday_api_key or not self.holiday_service:
                    return candidate
                if not self.holiday_service.is_holiday(candidate, holiday_api_key):
                    return candidate
            candidate += timedelta(days=1)

    def _notify(self, preferences, attempt: ReservationAttempt, success: bool) -> None:
        if not self.notifier or not preferences.notification_emails:
            return
        
        # Compact Subject
        weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][attempt.target_date.weekday()]
        status_str = "성공" if attempt.success else "실패"
        
        # If existing reservation, mark as success but maybe note it?
        # User requested: "Reservation Date / Result / Reserved Menu"
        menu_name = ""
        if attempt.details:
            menu_name = attempt.details.get("dispNm", "")
            
        subject = f"[예약 결과] {attempt.target_date.isoformat()} ({weekday_kr}) - {status_str}"
        if menu_name:
            subject += f" - {menu_name}"
        
        # Compact Body
        body_lines = [
            f"예약 날짜: {attempt.target_date.isoformat()} ({weekday_kr})",
            f"예약 결과: {status_str}",
        ]
        
        if menu_name:
             body_lines.append(f"예약한 메뉴: {menu_name}")
        
        if not attempt.success:
             body_lines.append(f"메시지: {attempt.message}")
             
        if attempt.attempted_menus:
             body_lines.append(f"선호 메뉴 순서: {', '.join(attempt.attempted_menus)}")

        if success:
             # Next reservation
             tz = pytz.timezone(preferences.timezone or self.timezone)
             holiday_api_key = os.environ.get("HOLIDAY_API_KEY")
             next_date = self._next_service_date(tz, holiday_api_key)
             next_weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][next_date.weekday()]
             body_lines.append(f"다음 예약 예정: {next_date.strftime('%Y-%m-%d')} ({next_weekday_kr})")

        body_lines.append("")
        body_lines.append("예약 확인: https://hcafe.hgreenfood.com/ctf/menu/reservation/menuReservation.do")
        
        self.notifier.send(subject, "\n".join(body_lines), preferences.notification_emails)
