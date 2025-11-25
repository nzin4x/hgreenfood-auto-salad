"""Lambda handler for updating user exclusion dates."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from core import ConfigStore

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def update_exclusion_dates_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """Update user exclusion dates."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"message": "Invalid JSON"})
        }

    user_id = body.get("userId")
    exclusion_dates = body.get("exclusionDates", [])

    if not user_id:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"message": "userId is required"})
        }

    config_store = ConfigStore()
    
    try:
        config_store.save_exclusion_dates(user_id, exclusion_dates)
        LOGGER.info(f"Updated exclusion dates for {user_id}: {exclusion_dates}")
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Exclusion dates updated successfully",
                "exclusionDates": exclusion_dates
            })
        }
    except Exception as error:
        LOGGER.exception(f"Failed to update exclusion dates for {user_id}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"message": f"Failed to update exclusion dates: {str(error)}"})
        }
