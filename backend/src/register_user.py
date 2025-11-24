import os
import json
import logging
import base64
from typing import Any, Dict
from core import ConfigStore

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)

def register_user_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    LOGGER.info("Received user registration event: %s", event)
    try:
        body = event.get("body")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode()
        payload = json.loads(body) if body else {}

        required_fields = ["userId", "password", "pin", "menuSeq", "floorNm", "email"]
        missing = [f for f in required_fields if not payload.get(f)]
        if missing:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": f"Missing fields: {', '.join(missing)}"})
            }

        user_id = payload["userId"]
        password = payload["password"]
        pin = payload["pin"]
        menu_seq = payload["menuSeq"]
        floor_nm = payload["floorNm"]
        email = payload["email"]
        
        # Validate email format
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid email format"})
            }

        # Encrypt password and pin (reuse existing crypto helpers)
        from core.crypto import encrypt
        master_password = os.environ.get("MASTER_PASSWORD")
        if not master_password:
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "Master password not configured"})
            }
        
        # encrypt() returns (encrypted_value, salt_b64)
        encrypted_password, salt = encrypt(password, master_password, None)
        encrypted_pin, _ = encrypt(pin, master_password, salt)

        # Device fingerprint (optional)
        device_fingerprint = payload.get("deviceFingerprint")
        devices = []
        if device_fingerprint:
            from datetime import datetime
            devices = [{
                "fingerprint": device_fingerprint,
                "registeredAt": datetime.utcnow().isoformat(),
                "lastAccessAt": datetime.utcnow().isoformat()
            }]
        
        item = {
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
            "userId": user_id,
            "userData_encrypted": encrypted_password,
            "pin_encrypted": encrypted_pin,
            "menuSeq": menu_seq,
            "floorNm": floor_nm,
            "email": email,
            "devices": devices,
            "_salt": salt,
        }
        config_store = ConfigStore()
        config_store.save_profile(item)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"message": "User registered successfully", "userId": user_id})
        }
    except Exception as error:
        LOGGER.exception("Error registering user")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(error)})
        }
