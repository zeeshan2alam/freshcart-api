"""Password hashing (stdlib scrypt) and JWT helpers."""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

import config

_N, _R, _P = 2**14, 8, 1


def _scrypt(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    return "scrypt${}${}".format(base64.b64encode(salt).decode(), base64.b64encode(_scrypt(password, salt)).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        return hmac.compare_digest(_scrypt(password, base64.b64decode(salt)), base64.b64decode(digest))
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, config.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
