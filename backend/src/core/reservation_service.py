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

    def run(self, user_id: str, master_password: str, service_date: Optional[date] = None) -> ReservationAttempt:
        preferences = self.config_store.get_user_preferences(user_id, master_password)
        tz_name = preferences.timezone or self.timezone
        tz = pytz.timezone(tz_name)
        holiday_api_key = os.environ.get("HOLIDAY_API_KEY")
        target_date = service_date or self._next_service_date(tz, holiday_api_key)

        if self.holiday_service and holiday_api_key:
            if self.holiday_service.is_holiday(target_date, holiday_api_key):
                attempt = ReservationAttempt(False, "Skipped due to public holiday", target_date, [])
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

        for menu_initial in preferences.menu_sequence:
            coner_dv_cd = self.reservation_client.menu_code_for(menu_initial)
            if not coner_dv_cd:
                continue
            attempted.append(menu_initial)
            result = self.reservation_client.reserve_menu(preferences.raw_payload, coner_dv_cd, target_prvd_dt)
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
        subject_prefix = "✅" if success else "⚠️"
        subject = f"{subject_prefix} H.GreenFood reservation result"
        body_lines = [
            f"User: {preferences.user_id}",
            f"Target date: {attempt.target_date.isoformat()}",
            f"Success: {attempt.success}",
            f"Message: {attempt.message}",
        ]
        if attempt.attempted_menus:
            body_lines.append(f"Attempted menus: {', '.join(attempt.attempted_menus)}")
        if attempt.details:
            body_lines.append(f"Details: {attempt.details}")
        self.notifier.send(subject, "\n".join(body_lines), preferences.notification_emails)
