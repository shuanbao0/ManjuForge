"""Password hashing, JWT signing, and credential encryption helpers."""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
from typing import Any, Optional

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from .instance import get_jwt_secret, get_master_key

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"
DEFAULT_TOKEN_TTL = dt.timedelta(hours=24)


# ── Password ──────────────────────────────────────────────────────────────
#
# bcrypt has a hard 72-byte input limit. We pre-hash with SHA-256 so that
# arbitrarily long passwords are supported uniformly without silent
# truncation, then bcrypt the resulting digest. This is the same trick
# Django and passlib's bcrypt_sha256 use.


def _prehash(plain: str) -> bytes:
    return hashlib.sha256(plain.encode("utf-8")).digest()


def hash_password(plain: str) -> str:
    if not plain:
        raise ValueError("password cannot be empty")
    return bcrypt.hashpw(_prehash(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_prehash(plain), hashed.encode("ascii"))
    except (ValueError, TypeError):
        logger.warning("verify_password: malformed hash encountered")
        return False


# ── JWT ───────────────────────────────────────────────────────────────────


class TokenError(Exception):
    """Base for token validation errors."""


class TokenExpiredError(TokenError):
    pass


class TokenInvalidError(TokenError):
    pass


def create_access_token(
    *,
    user_id: int,
    role: str,
    token_version: int,
    ttl: dt.timedelta = DEFAULT_TOKEN_TTL,
    extra: Optional[dict[str, Any]] = None,
) -> tuple[str, dt.datetime]:
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + ttl
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "tv": token_version,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if extra:
        claims.update(extra)
    token = jwt.encode(claims, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return token, exp


def decode_access_token(token: str) -> dict[str, Any]:
    if not token:
        raise TokenInvalidError("empty token")
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError(str(e)) from e
    except jwt.InvalidTokenError as e:
        raise TokenInvalidError(str(e)) from e


# ── Credential encryption (Fernet) ────────────────────────────────────────
#
# P3 will use these to store DASHSCOPE / OSS / etc. keys per user. Keeping
# the helpers here so the security surface lives in one file.


def _fernet() -> Fernet:
    return Fernet(get_master_key().encode("ascii"))


def encrypt_secret(plain: str) -> str:
    if plain is None:
        plain = ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        # Master key rotated or ciphertext tampered. Surface as empty so
        # callers can choose to re-prompt the user rather than crash.
        logger.warning("decrypt_secret: invalid Fernet token, returning empty")
        return ""
