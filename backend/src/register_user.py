import os
import json
import logging
import base64
import secrets
from typing import Any, Dict
from core import ConfigStore
from core.crypto import encrypt

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)

def register_user_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    LOGGER.info("=== REGISTER USER HANDLER STARTED ===")
    LOGGER.info("Received user registration event: %s", event)
    
    try:
        LOGGER.info("Step 1: Parsing request body")
        body = event.get("body")
        if event.get("isBase64Encoded"):
            LOGGER.info("Body is base64 encoded, decoding...")
            body = base64.b64decode(body).decode()
        payload = json.loads(body) if body else {}
        LOGGER.info("Parsed payload: %s", {k: v if k not in ['password', 'pin'] else '***' for k, v in payload.items()})

        LOGGER.info("Step 2: Validating required fields")
        # PIN is no longer required from user
        required_fields = ["userId", "password", "menuSeq", "floorNm", "email"]
        missing = [f for f in required_fields if not payload.get(f)]
        if missing:
            LOGGER.warning("Missing required fields: %s", missing)
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"message": f"Missing fields: {', '.join(missing)}"})
            }

        user_id = payload["userId"]
        password = payload["password"]
        # Generate random PIN if not provided (or always, as per user request "Just generate randomly")
        pin = f"{secrets.randbelow(1000000):06d}"
        menu_seq = payload["menuSeq"]
        floor_nm = payload["floorNm"]
        email = payload["email"]
        LOGGER.info("Extracted fields - userId: %s, email: %s, menuSeq: %s, floorNm: %s", user_id, email, menu_seq, floor_nm)
        
        LOGGER.info("Step 3: Validating email format")
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            LOGGER.warning("Invalid email format: %s", email)
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"message": "Invalid email format"})
            }

        LOGGER.info("Step 4: Encrypting user credentials (KMS)")
        try:
            # KMS encryption does not need master password
            encrypted_password, salt = encrypt(password)
            LOGGER.info("Password encrypted successfully")
            encrypted_pin, _ = encrypt(pin)
            LOGGER.info("PIN encrypted successfully")
        except Exception as e:
            LOGGER.error("Encryption failed: %s", str(e), exc_info=True)
            raise

        LOGGER.info("Step 5: Processing device fingerprint")
        device_fingerprint = payload.get("deviceFingerprint")
        devices = []
        if device_fingerprint:
            LOGGER.info("Device fingerprint provided: %s", device_fingerprint)
            from datetime import datetime
            devices = [{
                "fingerprint": device_fingerprint,
                "registeredAt": datetime.utcnow().isoformat(),
                "lastAccessAt": datetime.utcnow().isoformat()
            }]
        else:
            LOGGER.info("No device fingerprint provided")
        
        LOGGER.info("Step 6: Building DynamoDB item")
        item = {
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
            "userId": user_id,
            "userData_encrypted": encrypted_password,
            "pin_encrypted": encrypted_pin,
            "menuSeq": menu_seq,
            "floorNm": floor_nm,
            "email": email,
            "notificationEmails": [email],  # Enable reservation notifications by default
            "autoReservationEnabled": True,  # Enable auto-reservation by default
            "devices": devices,
            "_salt": salt,  # Kept for schema compatibility, though KMS doesn't use it for decryption
        }
        LOGGER.info("Item built with keys: %s", list(item.keys()))
        
        LOGGER.info("Step 7: Initializing ConfigStore")
        config_store = ConfigStore()
        LOGGER.info("ConfigStore initialized, table name: %s", config_store.table_name)
        
        LOGGER.info("Step 8: Saving profile to DynamoDB")
        config_store.save_profile(item)
        LOGGER.info("Profile saved successfully to DynamoDB")
        
        LOGGER.info("=== REGISTER USER HANDLER COMPLETED SUCCESSFULLY ===")
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"message": "User registered successfully", "userId": user_id})
        }
    except Exception as error:
        LOGGER.error("=== REGISTER USER HANDLER FAILED ===")
        LOGGER.exception("Error registering user: %s", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"message": str(error)})
        }

