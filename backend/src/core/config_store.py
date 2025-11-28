"""Abstraction over the DynamoDB configuration table used by the Lambdas."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import yaml

from .crypto import decrypt, encrypt
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

    def get_user_preferences(self, user_id: str) -> UserPreferences:
        item = self._fetch_profile_item(user_id)
        if not item:
            raise KeyError(f"Profile not found for user {user_id}")

        return self._build_preferences(item, user_id)

    def _build_preferences(self, item: Dict[str, Any], user_id: str) -> UserPreferences:
        password = self._decrypt_secret(item, "userData_encrypted")
        menu_seq = item.get("menuSeq", "").split(",")
        menu_sequence = [entry.strip() for entry in menu_seq if entry.strip()]
        floor_name = item.get("floorNm") or item.get("floor_name")
        payload = self._build_payload(item)
        holiday_api_key = self._extract_holiday_api_key(item)
        timezone = item.get("timezone") or os.environ.get("DEFAULT_TIMEZONE", "Asia/Seoul")
        notifications = item.get("notificationEmails") or item.get("notifications") or []
        if isinstance(notifications, str):
            notifications = [notifications]
        notifications = [addr for addr in notifications if addr]
        
        # If no notificationEmails, use email field as fallback
        if not notifications and item.get("email"):
            notifications = [item.get("email")]
        
        # Auto-reservation toggle (default: True)
        auto_reservation_enabled = item.get("autoReservationEnabled", True)
        if isinstance(auto_reservation_enabled, str):
            auto_reservation_enabled = auto_reservation_enabled.lower() in ('true', '1', 'yes')
        
        # Load exclusion dates
        exclusion_dates = item.get("exclusionDates", [])
        if isinstance(exclusion_dates, str):
            exclusion_dates = [exclusion_dates]
        exclusion_dates = [d for d in exclusion_dates if d]

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
            auto_reservation_enabled=auto_reservation_enabled,
            exclusion_dates=exclusion_dates,
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

    def _decrypt_secret(self, item: Dict[str, Any], key: str) -> str:
        encrypted = item.get(key)
        if not encrypted:
            raise KeyError(f"Missing encrypted payload '{key}'")
        # Salt is no longer used for decryption with KMS but might be present in legacy items
        return decrypt(encrypted)

    def _extract_holiday_api_key(self, item: Dict[str, Any]) -> Optional[str]:
        holiday_node = (
            item.get("data.go.kr", {})
            .get("api", {})
        )
        encrypted_key = holiday_node.get("key_encrypted") or item.get("holidayApiKey_encrypted")
        if not encrypted_key:
            return None
        return decrypt(encrypted_key)

    # Convenience helpers for potential future writes ---------------------

    def save_profile(self, item: Dict[str, Any]) -> None:
        import logging
        logger = logging.getLogger()
        try:
            logger.info("Saving profile for user: %s", item.get("userId"))
            self._table.put_item(Item=item)
            logger.info("Successfully saved profile for user: %s", item.get("userId"))
        except ClientError as error:
            logger.error("Failed to persist profile for %s: %s", item.get("userId"), error)
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
        return [item["userId"] for item in items if "userId" in item]
    
    def save_exclusion_dates(self, user_id: str, dates: List[str]) -> None:
        """Save user exclusion dates with auto-cleanup of old dates (> 1 month ago)"""
        from datetime import datetime, timedelta
        
        # Filter out dates older than 1 month
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        filtered_dates = [d for d in dates if d >= cutoff_date]
        
        key = {
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
        }
        
        try:
            self._table.update_item(
                Key=key,
                UpdateExpression="SET exclusionDates = :dates",
                ExpressionAttributeValues={":dates": filtered_dates},
            )
        except ClientError as error:
            raise RuntimeError(f"Failed to save exclusion dates for {user_id}: {error}") from error

    def save_holidays(self, year: int, month: int, dates: Set[str]) -> None:
        item = {
            "PK": "HOLIDAY",
            "SK": f"{year}{month:02d}",
            "dates": list(dates) if dates else [],  # Store as list to avoid empty set issues
        }
        try:
            self._table.put_item(Item=item)
        except ClientError as error:
            raise RuntimeError(f"Failed to save holidays: {error}") from error

    def get_holidays(self, year: int, month: int) -> Optional[Set[str]]:
        key = {
            "PK": "HOLIDAY",
            "SK": f"{year}{month:02d}",
        }
        try:
            response = self._table.get_item(Key=key)
        except ClientError:
            return None

        item = response.get("Item")
        if not item:
            return None

        dates = item.get("dates", [])
        return set(dates)

    def update_auto_reservation_status(self, user_id: str, enabled: bool) -> None:
        """Update the auto-reservation enabled status for a user"""
        import logging
        logger = logging.getLogger()
        key = {
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
        }
        try:
            logger.info("Updating auto-reservation status for user %s to %s", user_id, enabled)
            self._table.update_item(
                Key=key,
                UpdateExpression="SET autoReservationEnabled = :enabled",
                ExpressionAttributeValues={":enabled": enabled}
            )
            logger.info("Successfully updated auto-reservation status for user %s", user_id)
        except ClientError as error:
            logger.error("Failed to update auto-reservation status for %s: %s", user_id, error)
            raise RuntimeError(f"Failed to update auto-reservation status for {user_id}: {error}") from error

    def delete_profile(self, user_id: str) -> None:
        """Delete user profile (account deletion)"""
        import logging
        logger = logging.getLogger()
        key = {
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
        }
        try:
            logger.info("Deleting profile for user: %s", user_id)
            self._table.delete_item(Key=key)
            logger.info("Successfully deleted profile for user: %s", user_id)
        except ClientError as error:
            logger.error("Failed to delete profile for %s: %s", user_id, error)
            raise RuntimeError(f"Failed to delete profile for {user_id}: {error}") from error

    def update_user_settings(self, user_id: str, menu_sequence: list = None, floor_name: str = None, 
                            hg_user_id: str = None, hg_user_pw: str = None) -> None:
        """Update user settings (menu sequence, floor, and optionally HGreen credentials)"""
        import logging
        logger = logging.getLogger()
        key = {
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
        }
        
        update_parts = []
        attr_values = {}
        
        if menu_sequence is not None:
            menu_seq_str = ",".join(menu_sequence)
            update_parts.append("menuSeq = :menuSeq")
            attr_values[":menuSeq"] = menu_seq_str
        
        if floor_name is not None:
            update_parts.append("floorNm = :floorNm")
            attr_values[":floorNm"] = floor_name
        
        # Update HGreen ID if provided
        if hg_user_id is not None:
            update_parts.append("hgUserId = :hgUserId")
            attr_values[":hgUserId"] = hg_user_id
        
        # Update HGreen password if provided (encrypt it)
        if hg_user_pw is not None:
            encrypted_pw, _ = encrypt(hg_user_pw)
            update_parts.append("hgUserPw = :hgUserPw")
            attr_values[":hgUserPw"] = encrypted_pw
        
        if not update_parts:
            logger.warning("No fields to update for user %s", user_id)
            return
        
        update_expression = "SET " + ", ".join(update_parts)
        
        try:
            logger.info("Updating settings for user %s: %s", user_id, update_expression)
            self._table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=attr_values
            )
            logger.info("Successfully updated settings for user %s", user_id)
        except ClientError as error:
            logger.error("Failed to update settings for %s: %s", user_id, error)
            raise RuntimeError(f"Failed to update settings for {user_id}: {error}") from error

