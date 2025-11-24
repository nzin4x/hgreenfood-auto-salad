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
    ) -> None:
        self.endpoint = endpoint
        self.session = session or requests.Session()
        self.timeout = timeout
        self._cache: Dict[str, Set[str]] = {}

    def is_holiday(self, target: date, api_key: Optional[str]) -> bool:
        if not api_key:
            return False
        key = target.strftime("%Y%m")
        month_cache = self._cache.get(key)
        if month_cache is None:
            month_cache = self._fetch_month(target.year, target.month, api_key)
            self._cache[key] = month_cache
        return target.strftime("%Y%m%d") in month_cache

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
