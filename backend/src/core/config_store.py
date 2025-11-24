"""Abstraction over the DynamoDB configuration table used by the Lambdas."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import yaml

from .crypto import decrypt
from .models import UserPreferences


FALLBACK_DEFAULTS: Dict[str, Any] = {
    "osDvCd": "",
    "userCurrAppVer": "1.2.3",
    "mobiPhTrmlId": "",
    "bizplcCd": "196274",
    "mealDvCd": "0002",
    "rownum": 9,
    "dlvrPlcFloorNo": "9",
    "alphabetSeq": "I",
    "dlvrPlcFloorSeq": 9,
    "remainDeliQty": -1,
    "dlvrPlcNm": "현대오토에버 본사",
    "ordQty": 1,
    "totalCount": 12,
    "maxDelvQty": 0,
    "dlvrPlcSeq": 1,
    "dlvrRsvDvCd": 1,
    "dsppUseYn": "Y",
    "max_retry": 10,
    "retry_interval": 5,
}


class ConfigStore:
    """Loads encrypted per-user configuration from DynamoDB."""

    def __init__(
        self,
        table_name: Optional[str] = None,
        region_name: Optional[str] = None,
        dynamodb_resource=None,
        default_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.table_name = table_name or os.environ.get("CONFIG_TABLE_NAME")
        if not self.table_name:
            raise ValueError("CONFIG_TABLE_NAME env var is required")

        endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL")
        if endpoint_url:
            self._dynamodb = dynamodb_resource or boto3.resource(
                "dynamodb", region_name=region_name, endpoint_url=endpoint_url
            )
        else:
            self._dynamodb = dynamodb_resource or boto3.resource("dynamodb", region_name=region_name)
        self._table = self._dynamodb.Table(self.table_name)

        self._defaults = default_config or self._load_default_config()

    @staticmethod
    def _load_default_config() -> Dict[str, Any]:
        config_path = os.environ.get("DEFAULT_CONFIG_PATH", "config.default.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
                return {**FALLBACK_DEFAULTS, **loaded}
        return dict(FALLBACK_DEFAULTS)

    def get_user_preferences(self, user_id: str, master_password: str) -> UserPreferences:
        item = self._fetch_profile_item(user_id)
        if not item:
            raise KeyError(f"Profile not found for user {user_id}")

        return self._build_preferences(item, master_password, user_id)

    def _build_preferences(self, item: Dict[str, Any], master_password: str, user_id: str) -> UserPreferences:
        password = self._decrypt_secret(item, "userData_encrypted", master_password)
        menu_seq = item.get("menuSeq", "").split(",")
        menu_sequence = [entry.strip() for entry in menu_seq if entry.strip()]
        floor_name = item.get("floorNm") or item.get("floor_name")
        payload = self._build_payload(item)
        holiday_api_key = self._extract_holiday_api_key(item, master_password)
        timezone = item.get("timezone") or os.environ.get("DEFAULT_TIMEZONE", "Asia/Seoul")
        notifications = item.get("notificationEmails") or item.get("notifications") or []
        if isinstance(notifications, str):
            notifications = [notifications]
        notifications = [addr for addr in notifications if addr]

        return UserPreferences(
            user_id=item.get("userId", user_id),
            password=password,
            menu_sequence=menu_sequence,
            floor_name=floor_name or payload.get("floorNm", ""),
            raw_payload=payload,
            holiday_api_key=holiday_api_key,
            timezone=timezone,
            salt=item.get("_salt") or item.get("salt"),
            notification_emails=notifications,
        )

    def _fetch_profile_item(self, user_id: str) -> Optional[Dict[str, Any]]:
        key = {
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
        }
        try:
            result = self._table.get_item(Key=key)
        except ClientError as error:
            raise RuntimeError(f"Failed to load profile for {user_id}: {error}") from error
        return result.get("Item")

    def _build_payload(self, item: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(self._defaults)
        overrides = item.get("preferences") or {}
        payload.update(overrides)
        payload.setdefault("floorNm", item.get("floorNm"))
        payload.setdefault("menuSeq", item.get("menuSeq"))
        payload.setdefault("userId", item.get("userId"))
        payload.setdefault("osDvCd", item.get("osDvCd", ""))
        payload.setdefault("userCurrAppVer", item.get("userCurrAppVer", "1.2.3"))
        payload.setdefault("mobiPhTrmlId", item.get("mobiPhTrmlId", ""))
        return payload

    def _decrypt_secret(self, item: Dict[str, Any], key: str, master_password: str) -> str:
        encrypted = item.get(key)
        if not encrypted:
            raise KeyError(f"Missing encrypted payload '{key}'")
        salt = item.get("_salt") or item.get("salt")
        if not salt:
            raise KeyError("Missing salt for encrypted payload")
        return decrypt(encrypted, master_password, salt)

    def _extract_holiday_api_key(self, item: Dict[str, Any], master_password: str) -> Optional[str]:
        holiday_node = (
            item.get("data.go.kr", {})
            .get("api", {})
        )
        encrypted_key = holiday_node.get("key_encrypted") or item.get("holidayApiKey_encrypted")
        if not encrypted_key:
            return None
        holiday_salt = holiday_node.get("salt") or holiday_node.get("_salt") or item.get("holidayApiKey_salt")
        if not holiday_salt:
            holiday_salt = item.get("_salt") or item.get("salt")
        return decrypt(encrypted_key, master_password, holiday_salt)

    # Convenience helpers for potential future writes ---------------------

    def save_profile(self, item: Dict[str, Any]) -> None:
        try:
            self._table.put_item(Item=item)
        except ClientError as error:
            raise RuntimeError(f"Failed to persist profile for {item.get('userId')}: {error}") from error

    def list_users(self) -> List[str]:
        index_name = os.environ.get("CONFIG_GSI_PK")
        try:
            if index_name:
                response = self._table.query(
                    KeyConditionExpression=Key("SK").eq("PROFILE"),
                    IndexName=index_name,
                )
            else:
                response = self._table.scan(
                    ProjectionExpression="userId"
                )
        except ClientError as error:
            raise RuntimeError(f"Failed to query configuration table: {error}") from error
        items = response.get("Items", [])
        return [entry.get("userId") for entry in items]
