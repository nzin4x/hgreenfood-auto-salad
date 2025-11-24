from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class UserPreferences:
    """Hydrated user profile values required for reservation requests."""

    user_id: str
    password: str
    menu_sequence: List[str]
    floor_name: str
    raw_payload: Dict[str, Any]
    holiday_api_key: Optional[str] = None
    timezone: Optional[str] = None
    salt: Optional[str] = None
    notification_emails: List[str] = field(default_factory=list)
    auto_reservation_enabled: bool = True


@dataclass
class ReservationAttempt:
    """Result wrapper for a single reservation execution."""

    success: bool
    message: str
    target_date: date
    attempted_menus: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoginResult:
    success: bool
    message: str
    response_payload: Optional[Dict[str, Any]] = None


@dataclass
class ApiCallResult:
    success: bool
    error_code: Optional[int]
    error_message: Optional[str]
    raw: Dict[str, Any]
