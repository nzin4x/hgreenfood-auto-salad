"""Minimal Fernet helpers reused by Lambda functions."""

import base64
import os
from typing import Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _derive_key(password: str, salt: bytes, iterations: int = 100_000) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def decrypt(encrypted_value: str, password: str, salt_b64: str) -> str:
    salt = base64.b64decode(salt_b64)
    key = _derive_key(password, salt)
    return Fernet(key).decrypt(encrypted_value.encode()).decode()


def encrypt(value: str, password: str, salt_b64: Optional[str] = None) -> Tuple[str, str]:
    if salt_b64 is None:
        salt = os.urandom(16)
    else:
        salt = base64.b64decode(salt_b64)
    key = _derive_key(password, salt)
    token = Fernet(key).encrypt(value.encode()).decode()
    return token, base64.b64encode(salt).decode()
