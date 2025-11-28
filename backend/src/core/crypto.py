"""KMS based crypto helpers."""

import base64
import os
import logging
from typing import Optional, Tuple

import boto3
from botocore.exceptions import ClientError

LOGGER = logging.getLogger()

def _get_kms_client():
    return boto3.client('kms')

def _get_key_id():
    return os.environ.get("KMS_KEY_ID", "alias/hgreenfood-key")

def decrypt(encrypted_value: str, _password: Optional[str] = None, _salt_b64: Optional[str] = None) -> str:
    """
    Decrypts a value using AWS KMS.
    The password and salt arguments are kept for backward compatibility with the signature 
    but are ignored as KMS handles key management.
    """
    try:
        # If the value is not base64 encoded, it might be legacy or plain text (shouldn't happen if flow is strict)
        # But we assume input is the base64 encoded ciphertext blob
        ciphertext_blob = base64.b64decode(encrypted_value)
        
        kms = _get_kms_client()
        response = kms.decrypt(
            CiphertextBlob=ciphertext_blob
        )
        
        return response['Plaintext'].decode('utf-8')
    except Exception as e:
        LOGGER.error(f"KMS decryption failed: {e}")
        raise

def encrypt(value: str, _password: Optional[str] = None, _salt_b64: Optional[str] = None) -> Tuple[str, str]:
    """
    Encrypts a value using AWS KMS.
    Returns (encrypted_value_b64, dummy_salt).
    The password and salt arguments are kept for backward compatibility but ignored.
    """
    try:
        kms = _get_kms_client()
        key_id = _get_key_id()
        
        response = kms.encrypt(
            KeyId=key_id,
            Plaintext=value.encode('utf-8')
        )
        
        ciphertext_blob = response['CiphertextBlob']
        encrypted_b64 = base64.b64encode(ciphertext_blob).decode('utf-8')
        
        # Return dummy salt to maintain tuple signature expected by callers for now
        return encrypted_b64, "kms_managed"
    except Exception as e:
        LOGGER.error(f"KMS encryption failed: {e}")
        raise
