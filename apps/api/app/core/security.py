import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.core.config import settings

# Passlib pwd context with Argon2 fallback to bcrypt if needed
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        verified = pwd_context.verify(plain_password, hashed_password)
        return bool(verified)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    hashed = pwd_context.hash(password)
    return str(hashed)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None, extra_claims: dict[str, Any] | None = None) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return str(encoded_jwt)


def decode_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    if not isinstance(payload, dict):
        raise ValueError("Decoded token payload is not a dictionary")
    return payload


# Fernet token encryption for calendar tokens
def _get_fernet() -> Fernet:
    # Key must be 32 url-safe base64-encoded bytes
    key = settings.ENCRYPTION_KEY.encode('utf-8')
    if len(key) != 44:
        # Generate deterministic 32-byte key from SECRET_KEY if invalid
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest())
    return Fernet(key)


def encrypt_data(data: dict[str, Any]) -> str:
    f = _get_fernet()
    raw = json.dumps(data).encode('utf-8')
    return f.encrypt(raw).decode('utf-8')


def decrypt_data(token_str: str) -> dict[str, Any]:
    f = _get_fernet()
    decrypted = f.decrypt(token_str.encode("utf-8"))
    payload: dict[str, Any] = json.loads(decrypted.decode("utf-8"))
    return payload
