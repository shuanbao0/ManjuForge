"""Pydantic request/response models for the auth subsystem."""

from __future__ import annotations

import datetime as dt
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from .models import Role, Status


_PASSWORD_MIN = 8
_PASSWORD_MAX = 128


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _validate_password(value: str) -> str:
    if not value or len(value) < _PASSWORD_MIN:
        raise ValueError(f"password must be at least {_PASSWORD_MIN} characters")
    if len(value) > _PASSWORD_MAX:
        raise ValueError(f"password must be at most {_PASSWORD_MAX} characters")
    return value


class _EmailMixin(BaseModel):
    email: str = Field(..., max_length=255)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = _normalize_email(v)
        # Loose RFC-ish check; we want to accept what real users type without
        # pulling email_validator as a hard dep.
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("invalid email")
        return v


class SetupRequest(_EmailMixin):
    password: str
    display_name: str = ""

    @field_validator("password")
    @classmethod
    def _pwd(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("display_name")
    @classmethod
    def _name(cls, v: str) -> str:
        return v.strip()[:100]


class LoginRequest(_EmailMixin):
    password: str = Field(..., min_length=1, max_length=_PASSWORD_MAX)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=_PASSWORD_MAX)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _pwd(cls, v: str) -> str:
        return _validate_password(v)


class CreateUserRequest(_EmailMixin):
    password: str
    role: Role = Role.USER
    display_name: str = ""

    @field_validator("password")
    @classmethod
    def _pwd(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("display_name")
    @classmethod
    def _name(cls, v: str) -> str:
        return v.strip()[:100]


class UpdateUserRequest(BaseModel):
    role: Optional[Role] = None
    status: Optional[Status] = None
    display_name: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator("display_name")
    @classmethod
    def _name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip()[:100]

    @field_validator("new_password")
    @classmethod
    def _pwd(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return _validate_password(v)


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    status: str
    display_name: str
    is_active: bool
    last_login_at: Optional[dt.datetime] = None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: dt.datetime
    user: UserOut


class SetupStatus(BaseModel):
    needs_setup: bool
    user_count: int


class AdminStats(BaseModel):
    user_count: int
    active_user_count: int
    admin_count: int
    disabled_user_count: int
    last_login_at: Optional[dt.datetime] = None


class AuditLogOut(BaseModel):
    id: int
    action: str
    actor_user_id: Optional[int] = None
    actor_email: str
    target_user_id: Optional[int] = None
    target_email: str
    detail: str
    ip: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class SettingsOut(BaseModel):
    """Instance-wide flags. P1 ships these but does not yet enforce them all;
    P2/P3 will gate behavior on them."""

    registration_enabled: bool = False
    invitation_required: bool = False
    default_user_role: Role = Role.USER


class SettingsUpdate(BaseModel):
    registration_enabled: Optional[bool] = None
    invitation_required: Optional[bool] = None
    default_user_role: Optional[Role] = None
