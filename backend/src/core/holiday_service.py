"""Lightweight wrapper around the public holiday API with simple caching."""

from __future__ import annotations

from datetime import date
from typing import Dict, Optional, Set

import requests
import xml.etree.ElementTree as ET


class HolidayService:
    def __init__(
        self,
        endpoint: str = "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo",
        session: Optional[requests.Session] = None,
        timeout: int = 10,
        config_store: Optional[Any] = None,  # Avoid circular import type hint if possible, or use Any
    ) -> None:
        self.endpoint = endpoint
        self.session = session or requests.Session()
        self.timeout = timeout
        self.config_store = config_store
        self._cache: Dict[str, Set[str]] = {}

    def is_holiday(self, target: date, api_key: Optional[str]) -> bool:
        if not api_key:
            return False
        
        # 1. Check local memory cache
        key = target.strftime("%Y%m")
        if key in self._cache:
            return target.strftime("%Y%m%d") in self._cache[key]

        # 2. Check DynamoDB (ConfigStore)
        if self.config_store:
            stored_holidays = self.config_store.get_holidays(target.year, target.month)
            if stored_holidays is not None:
                self._cache[key] = stored_holidays
                return target.strftime("%Y%m%d") in stored_holidays

        # 3. Fetch from API
        month_cache = self._fetch_month(target.year, target.month, api_key)
        self._cache[key] = month_cache
        
        # 4. Save to DynamoDB
        if self.config_store:
            try:
                self.config_store.save_holidays(target.year, target.month, month_cache)
            except Exception:
                # Log error but don't fail the check
                pass
                
        return target.strftime("%Y%m%d") in month_cache

    def fetch_and_save_holidays(self, year: int, month: int, api_key: str) -> Set[str]:
        holidays = self._fetch_month(year, month, api_key)
        if self.config_store:
            self.config_store.save_holidays(year, month, holidays)
        return holidays

    def _fetch_month(self, year: int, month: int, api_key: str) -> Set[str]:
        params = {
            "serviceKey": api_key,
            "solYear": str(year),
            "solMonth": f"{month:02d}",
        }
        response = self.session.get(self.endpoint, params=params, timeout=self.timeout)
        response.raise_for_status()
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            raise RuntimeError("Failed to parse holiday API response") from exc

        result_code = root.findtext(".//resultCode")
        if result_code and result_code != "00":
            result_msg = root.findtext(".//resultMsg") or "Unknown error"
            raise RuntimeError(f"Holiday API error {result_code}: {result_msg}")

        locdates = {node.text for node in root.findall(".//item/locdate") if node.text}
        return locdates
