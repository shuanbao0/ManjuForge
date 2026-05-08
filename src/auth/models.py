"""SQLAlchemy ORM models for the auth subsystem."""

from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Role(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class Status(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


def _utcnow() -> dt.datetime:
    # SQLite has no native tz support, so we store naive UTC throughout to
    # avoid tz-aware vs tz-naive comparison errors when reading rows back.
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class User(Base):
    """Application user. Soft-deletable; e-mail is unique among non-deleted rows."""

    __tablename__ = "users"
    __table_args__ = (
        # Partial-style uniqueness: enforced at the service layer too, since
        # SQLite doesn't easily support partial unique indexes via SQLAlchemy
        # core without dialect tricks. We index for fast lookups.
        Index("ix_users_email_lower", "email"),
        Index("ix_users_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=Role.USER.value)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=Status.ACTIVE.value)

    # Bumped on password change / forced logout to invalidate outstanding JWTs.
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    last_active_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    credentials: Mapped[list["UserCredential"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN.value

    @property
    def is_active(self) -> bool:
        return self.status == Status.ACTIVE.value and self.deleted_at is None


class UserCredential(Base):
    """Per-user encrypted credentials (P3 will populate, P1 just defines schema)."""

    __tablename__ = "user_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_credentials_user_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value_encrypted: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user: Mapped["User"] = relationship(back_populates="credentials")


class ModelInstanceRow(Base):
    """A user-configured model instance.

    Concept: each row represents one usable model — pairing a vendor + a
    specific ``model_name`` with the user's credentials and a friendly
    label. Projects reference instances via :pyattr:`id`, so swapping a
    project's LLM is as simple as picking a different instance id.

    Credentials are stored as a Fernet-encrypted JSON blob in
    :pyattr:`encrypted_credentials`; everything else is plain text.

    The unique constraint enforces "at most one default per user per type",
    relying on a partial index emulated at the service layer for SQLite.
    """

    __tablename__ = "model_instances"
    __table_args__ = (
        Index("ix_model_instances_user_type", "user_id", "instance_type"),
        Index("ix_model_instances_user_default", "user_id", "instance_type", "is_default"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    instance_type: Mapped[str] = mapped_column(String(16), nullable=False)
    vendor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False, default="")
    base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    extra_params_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )


class Setting(Base):
    """Instance-wide key/value flags (e.g. registration_enabled)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )


class AuditLog(Base):
    """Append-only record of auth/admin actions for forensics and dashboards.

    Kept minimal on purpose: actor → action → optional target → details JSON.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    target_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
