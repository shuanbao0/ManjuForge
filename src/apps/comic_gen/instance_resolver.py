"""Resolve ``ModelSettings.*_instance_id`` → :class:`ModelInstance`.

This is the bridge between the project-level "which instance?" reference
and the runtime "what creds + model name + base url should I use?" lookup.
Pipeline code calls :func:`scoped_instance` (Context Manager) which:

1. Looks up the user's ``ModelInstance`` by id (or by default if id is ``None``).
2. Pushes it into the runtime via :func:`src.runtime.with_instance`.
3. Yields the resolved instance (or ``None``) so the caller can read the
   ``model_name`` to forward to the underlying client.

Keeping the lookup centralized means model_settings can grow new fields
without scattering DB-access code through ``pipeline.py`` /
``assets.py`` / ``video.py``.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from ...auth.db import session_scope
from ...models.instance import InstanceType, ModelInstance
from ...models.instance_repository import InstanceRepository
from ...runtime import current_user_id, with_instance


def load_instance(
    instance_id: Optional[str], instance_type: InstanceType
) -> Optional[ModelInstance]:
    """Load instance by id, or fall back to the user's default for that type.

    Returns ``None`` outside an authenticated request (e.g. CLI scripts) so
    callers can fall through to env-only behavior gracefully.
    """
    user_id = current_user_id()
    if user_id is None:
        return None
    with session_scope() as session:
        repo = InstanceRepository(session)
        if instance_id:
            return repo.get(instance_id, user_id)
        return repo.get_default(user_id, instance_type)


@contextmanager
def scoped_instance(
    instance_id: Optional[str], instance_type: InstanceType
) -> Iterator[Optional[ModelInstance]]:
    """Resolve and bind the instance to the current call.

    Usage::

        with scoped_instance(script.model_settings.t2i_instance_id, InstanceType.T2I) as inst:
            model_name = inst.model_name if inst else "wan2.6-t2i"
            asset_generator.generate_character(..., model_name=model_name)
    """
    instance = load_instance(instance_id, instance_type)
    with with_instance(instance):
        yield instance


def model_name_or(default: str, instance: Optional[ModelInstance]) -> str:
    return instance.model_name if instance else default


__all__ = ["load_instance", "scoped_instance", "model_name_or"]
