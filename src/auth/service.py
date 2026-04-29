"""Auth/admin business logic. All callers pass an open SQLAlchemy session."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import schemas, security
from .models import AuditLog, Role, Setting, Status, User

logger = logging.getLogger(__name__)


# ── Errors ────────────────────────────────────────────────────────────────


class AuthError(Exception):
    """Base for auth/admin domain errors. Carries a stable code for the API."""

    code: str = "AUTH_ERROR"
    http_status: int = 400

    def __init__(self, message: str = "", *, code: Optional[str] = None, http_status: Optional[int] = None):
        super().__init__(message or self.__class__.__name__)
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status


class SetupAlreadyCompleted(AuthError):
    code = "SETUP_ALREADY_COMPLETED"
    http_status = 409


class EmailAlreadyExists(AuthError):
    code = "EMAIL_EXISTS"
    http_status = 409


class InvalidCredentials(AuthError):
    code = "INVALID_CREDENTIALS"
    http_status = 401


class UserNotActive(AuthError):
    code = "USER_NOT_ACTIVE"
    http_status = 403


class UserNotFound(AuthError):
    code = "USER_NOT_FOUND"
    http_status = 404


class CannotDemoteLastAdmin(AuthError):
    code = "CANNOT_DEMOTE_LAST_ADMIN"
    http_status = 409


# ── Queries ───────────────────────────────────────────────────────────────


def _live(session: Session):
    return select(User).where(User.deleted_at.is_(None))


def get_user(session: Session, user_id: int) -> Optional[User]:
    return session.scalar(_live(session).where(User.id == user_id))


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    norm = email.strip().lower()
    return session.scalar(_live(session).where(func.lower(User.email) == norm))


def count_live_users(session: Session) -> int:
    return int(session.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None))) or 0)


def count_admins(session: Session, *, exclude_id: Optional[int] = None) -> int:
    stmt = select(func.count(User.id)).where(
        User.deleted_at.is_(None),
        User.role == Role.ADMIN.value,
        User.status == Status.ACTIVE.value,
    )
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return int(session.scalar(stmt) or 0)


def list_users(session: Session) -> list[User]:
    return list(session.scalars(_live(session).order_by(User.created_at.asc())))


# ── Commands ──────────────────────────────────────────────────────────────


def setup_status(session: Session) -> schemas.SetupStatus:
    n = count_live_users(session)
    return schemas.SetupStatus(needs_setup=n == 0, user_count=n)


def bootstrap_admin(session: Session, payload: schemas.SetupRequest) -> User:
    """Create the very first admin. Refuses if any user already exists."""
    if count_live_users(session) > 0:
        raise SetupAlreadyCompleted("setup already completed")

    user = User(
        email=payload.email,
        password_hash=security.hash_password(payload.password),
        role=Role.ADMIN.value,
        status=Status.ACTIVE.value,
        display_name=payload.display_name,
    )
    session.add(user)
    session.flush()
    logger.info("bootstrap_admin: created admin id=%s email=%s", user.id, user.email)
    return user


def login(session: Session, payload: schemas.LoginRequest) -> tuple[User, str, dt.datetime]:
    user = get_user_by_email(session, payload.email)
    if user is None or not security.verify_password(payload.password, user.password_hash):
        raise InvalidCredentials("invalid email or password")
    if not user.is_active:
        raise UserNotActive("user is not active")

    user.last_login_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    user.last_active_at = user.last_login_at
    session.flush()

    token, expires_at = security.create_access_token(
        user_id=user.id, role=user.role, token_version=user.token_version
    )
    return user, token, expires_at


def issue_token(user: User) -> tuple[str, dt.datetime]:
    return security.create_access_token(
        user_id=user.id, role=user.role, token_version=user.token_version
    )


def change_password(session: Session, user: User, current: str, new: str) -> None:
    if not security.verify_password(current, user.password_hash):
        raise InvalidCredentials("current password is incorrect")
    user.password_hash = security.hash_password(new)
    user.token_version += 1
    session.flush()


def admin_create_user(session: Session, payload: schemas.CreateUserRequest) -> User:
    if get_user_by_email(session, payload.email) is not None:
        raise EmailAlreadyExists("email already in use")
    user = User(
        email=payload.email,
        password_hash=security.hash_password(payload.password),
        role=payload.role.value,
        status=Status.ACTIVE.value,
        display_name=payload.display_name,
    )
    session.add(user)
    session.flush()
    return user


def admin_update_user(session: Session, user_id: int, payload: schemas.UpdateUserRequest) -> User:
    user = get_user(session, user_id)
    if user is None:
        raise UserNotFound()

    if payload.role is not None and payload.role.value != user.role:
        if user.role == Role.ADMIN.value and payload.role == Role.USER:
            if count_admins(session, exclude_id=user.id) == 0:
                raise CannotDemoteLastAdmin("cannot demote the only remaining admin")
        user.role = payload.role.value

    if payload.status is not None and payload.status.value != user.status:
        if (
            user.role == Role.ADMIN.value
            and payload.status == Status.DISABLED
            and count_admins(session, exclude_id=user.id) == 0
        ):
            raise CannotDemoteLastAdmin("cannot disable the only remaining admin")
        user.status = payload.status.value

    if payload.display_name is not None:
        user.display_name = payload.display_name

    if payload.new_password:
        user.password_hash = security.hash_password(payload.new_password)
        user.token_version += 1

    session.flush()
    return user


def admin_delete_user(session: Session, user_id: int, *, requested_by: int) -> None:
    if user_id == requested_by:
        raise AuthError("cannot delete yourself", code="CANNOT_DELETE_SELF", http_status=409)
    user = get_user(session, user_id)
    if user is None:
        raise UserNotFound()
    if user.role == Role.ADMIN.value and count_admins(session, exclude_id=user.id) == 0:
        raise CannotDemoteLastAdmin("cannot delete the only remaining admin")
    user.deleted_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    user.status = Status.DISABLED.value
    user.token_version += 1
    session.flush()

    # Drop cached per-user provider/storage instances and the per-user
    # ComicGenPipeline so the slot is fully freed. Wrapped in try/except
    # because none of these caches must block user deletion.
    for _evict in (_evict_storage_caches, _evict_pipeline_cache):
        try:
            _evict(user_id)
        except Exception:  # pragma: no cover
            logger.exception("Cache eviction failed for user_id=%s", user_id)


def _evict_storage_caches(user_id: int) -> None:
    from ..utils.oss_utils import OSSImageUploader
    from ..utils.object_storage import ObjectStorageClient

    OSSImageUploader.reset_instance(user_id)
    ObjectStorageClient.reset_cache(user_id)


def _evict_pipeline_cache(user_id: int) -> None:
    from ..apps.comic_gen.pipeline_factory import evict_user, _user_data_root

    evict_user(user_id)

    # Soft-delete on disk: rename ``output/users/<uid>`` to a sibling
    # ``.deleted-<uid>-<ts>`` so the data is no longer reachable by a
    # newly-created user that happens to land on the same numeric id, but
    # an operator can recover it manually if the deletion was a mistake.
    import os
    import shutil
    import time

    root = _user_data_root(user_id)
    if os.path.isdir(root):
        parent = os.path.dirname(root)
        graveyard = os.path.join(parent, f".deleted-{user_id}-{int(time.time())}")
        try:
            shutil.move(root, graveyard)
        except Exception:  # pragma: no cover
            logger.exception("Failed to retire user data dir %s", root)


def touch_active(session: Session, user: User) -> None:
    """Best-effort last_active_at update. Swallow errors — never block requests."""
    try:
        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        # Skip if recently touched (cheap throttle to avoid write per request)
        if user.last_active_at and (now - user.last_active_at).total_seconds() < 60:
            return
        user.last_active_at = now
        session.commit()
    except Exception:  # pragma: no cover
        logger.exception("touch_active failed for user %s", user.id)
        session.rollback()


def force_logout(session: Session, user_id: int) -> User:
    user = get_user(session, user_id)
    if user is None:
        raise UserNotFound()
    user.token_version += 1
    session.flush()
    return user


# ── Audit log ─────────────────────────────────────────────────────────────


def record_audit(
    session: Session,
    *,
    action: str,
    actor: Optional[User] = None,
    target: Optional[User] = None,
    detail: str = "",
    ip: str = "",
) -> AuditLog:
    entry = AuditLog(
        action=action[:64],
        actor_user_id=(actor.id if actor else None),
        actor_email=(actor.email if actor else "")[:255],
        target_user_id=(target.id if target else None),
        target_email=(target.email if target else "")[:255],
        detail=detail[:4096],
        ip=ip[:64],
    )
    session.add(entry)
    session.flush()
    return entry


def list_audit_logs(session: Session, *, limit: int = 100, offset: int = 0) -> list[AuditLog]:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(stmt))


# ── Stats ─────────────────────────────────────────────────────────────────


def admin_stats(session: Session) -> schemas.AdminStats:
    total = count_live_users(session)
    admins = int(session.scalar(
        select(func.count(User.id)).where(
            User.deleted_at.is_(None),
            User.role == Role.ADMIN.value,
            User.status == Status.ACTIVE.value,
        )
    ) or 0)
    actives = int(session.scalar(
        select(func.count(User.id)).where(
            User.deleted_at.is_(None),
            User.status == Status.ACTIVE.value,
        )
    ) or 0)
    disabled = total - actives
    last_login = session.scalar(
        select(func.max(User.last_login_at)).where(User.deleted_at.is_(None))
    )
    return schemas.AdminStats(
        user_count=total,
        active_user_count=actives,
        admin_count=admins,
        disabled_user_count=disabled,
        last_login_at=last_login,
    )


# ── Settings ──────────────────────────────────────────────────────────────


_SETTINGS_DEFAULTS: dict[str, str] = {
    "registration_enabled": "false",
    "invitation_required": "false",
    "default_user_role": Role.USER.value,
}


def _setting_get(session: Session, key: str) -> Optional[str]:
    row = session.get(Setting, key)
    return row.value if row else None


def _setting_set(session: Session, key: str, value: str) -> None:
    row = session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value


def get_settings(session: Session) -> schemas.SettingsOut:
    def _bool(key: str) -> bool:
        v = _setting_get(session, key)
        if v is None:
            v = _SETTINGS_DEFAULTS.get(key, "false")
        return v.strip().lower() in ("1", "true", "yes", "on")

    role_raw = _setting_get(session, "default_user_role") or _SETTINGS_DEFAULTS["default_user_role"]
    try:
        role = Role(role_raw)
    except ValueError:
        role = Role.USER

    return schemas.SettingsOut(
        registration_enabled=_bool("registration_enabled"),
        invitation_required=_bool("invitation_required"),
        default_user_role=role,
    )


def update_settings(session: Session, payload: schemas.SettingsUpdate) -> schemas.SettingsOut:
    if payload.registration_enabled is not None:
        _setting_set(session, "registration_enabled", "true" if payload.registration_enabled else "false")
    if payload.invitation_required is not None:
        _setting_set(session, "invitation_required", "true" if payload.invitation_required else "false")
    if payload.default_user_role is not None:
        _setting_set(session, "default_user_role", payload.default_user_role.value)
    session.flush()
    return get_settings(session)
