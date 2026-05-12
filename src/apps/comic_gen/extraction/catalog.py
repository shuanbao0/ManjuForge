"""``EntityCatalog`` — Repository adapter over ``Series`` + ``Script``.

The extraction package needs to answer two questions:

1. "What characters/scenes/props already exist for this project?"
2. "Add this newly-discovered entity (or reuse an existing one)."

Today those answers live in two places — ``Series.characters/scenes/props``
(shared across episodes) and ``Script.characters/scenes/props`` (per-episode
local fallback). Sprinkling that logic across the extraction strategies
would couple them to data layout. ``EntityCatalog`` centralises it so
strategies only deal with a single, simple API.

Series-first policy
~~~~~~~~~~~~~~~~~~~
When a script belongs to a Series, **new entities are written to the
Series** (shared library). The episode keeps only references via
``Script.used_*_ids`` — this is what makes cross-episode consistency
possible. For standalone scripts (no ``series_id``) the catalog falls
back to writing into ``Script.characters/...``.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..models import Character, GenerationStatus, Prop, Scene, Script, Series
from .dedup import CharacterMatchSpec, PropMatchSpec, SceneMatchSpec


class EntityCatalog:
    """Series-first, script-fallback entity store.

    All ``upsert_*`` methods are idempotent: they never overwrite the
    matched entity's fields. The rationale is that, by the time the user
    has invested in generating images/voice for a character, an LLM
    re-read of the script must not silently mutate the canonical
    description out from under them. Re-extraction only *adds* — never
    rewrites — existing rows.
    """

    def __init__(self, script: Script, series: Optional[Series] = None):
        self._script = script
        self._series = series
        self._char_spec = CharacterMatchSpec()
        self._scene_spec = SceneMatchSpec()
        self._prop_spec = PropMatchSpec()

    # ── Read API ───────────────────────────────────────────────────────

    @property
    def is_series_backed(self) -> bool:
        return self._series is not None

    @property
    def characters(self) -> List[Character]:
        if self._series is not None:
            return list(self._series.characters)
        return list(self._script.characters)

    @property
    def scenes(self) -> List[Scene]:
        if self._series is not None:
            return list(self._series.scenes)
        return list(self._script.scenes)

    @property
    def props(self) -> List[Prop]:
        if self._series is not None:
            return list(self._series.props)
        return list(self._script.props)

    def summary_for_llm(self) -> Dict[str, List[Dict[str, Any]]]:
        """Compact projection fed back to the LLM as "already-known" context.

        Includes just enough metadata for matching (name + gender for
        characters, name + time for scenes, name for props). Heavy fields
        like full descriptions are omitted to keep prompt tokens small.
        """
        return {
            "characters": [
                {
                    "id": c.id,
                    "name": c.name,
                    "gender": c.gender,
                    "age": c.age,
                }
                for c in self.characters
            ],
            "scenes": [
                {
                    "id": s.id,
                    "name": s.name,
                    "time_of_day": s.time_of_day,
                }
                for s in self.scenes
            ],
            "props": [{"id": p.id, "name": p.name} for p in self.props],
        }

    # ── Write API ──────────────────────────────────────────────────────

    def upsert_character(self, candidate: Dict[str, Any]) -> Tuple[Character, bool]:
        """Match-or-create. Returns ``(entity, created)``.

        ``created=True`` means a fresh row was appended; ``False`` means
        the candidate matched and the existing row was returned verbatim.
        """
        for existing in self._existing_characters():
            if self._char_spec.is_same(existing, candidate):
                return existing, False
        new_char = Character(
            id=str(uuid.uuid4()),
            name=candidate.get("name", "Unknown"),
            description=candidate.get("description", ""),
            age=candidate.get("age"),
            gender=candidate.get("gender"),
            clothing=candidate.get("clothing"),
            visual_weight=int(candidate.get("visual_weight", 3) or 3),
            status=GenerationStatus.PENDING,
        )
        self._append_character(new_char)
        return new_char, True

    def upsert_scene(self, candidate: Dict[str, Any]) -> Tuple[Scene, bool]:
        for existing in self._existing_scenes():
            if self._scene_spec.is_same(existing, candidate):
                return existing, False
        new_scene = Scene(
            id=str(uuid.uuid4()),
            name=candidate.get("name", "Unknown"),
            description=candidate.get("description", ""),
            time_of_day=candidate.get("time_of_day"),
            lighting_mood=candidate.get("lighting_mood"),
            visual_weight=int(candidate.get("visual_weight", 3) or 3),
            status=GenerationStatus.PENDING,
        )
        self._append_scene(new_scene)
        return new_scene, True

    def upsert_prop(self, candidate: Dict[str, Any]) -> Tuple[Prop, bool]:
        for existing in self._existing_props():
            if self._prop_spec.is_same(existing, candidate):
                return existing, False
        new_prop = Prop(
            id=str(uuid.uuid4()),
            name=candidate.get("name", "Unknown"),
            description=candidate.get("description", ""),
            status=GenerationStatus.PENDING,
        )
        self._append_prop(new_prop)
        return new_prop, True

    # ── Episode linkage ────────────────────────────────────────────────

    def link_to_episode(
        self,
        character_ids: Iterable[str] = (),
        scene_ids: Iterable[str] = (),
        prop_ids: Iterable[str] = (),
    ) -> None:
        """Record "this episode references these Series entities".

        Used by the incremental strategy to keep
        ``Script.used_*_ids`` up to date without duplicating the heavy
        entity rows into the per-episode script. Idempotent.
        """
        self._merge_ids(self._script.used_character_ids, character_ids)
        self._merge_ids(self._script.used_scene_ids, scene_ids)
        self._merge_ids(self._script.used_prop_ids, prop_ids)
        self._script.updated_at = time.time()
        if self._series is not None:
            self._series.updated_at = time.time()

    # ── Internals ──────────────────────────────────────────────────────

    @staticmethod
    def _merge_ids(target: List[str], new_ids: Iterable[str]) -> None:
        seen = set(target)
        for nid in new_ids:
            if nid and nid not in seen:
                target.append(nid)
                seen.add(nid)

    def _existing_characters(self) -> Iterable[Character]:
        if self._series is not None:
            return self._series.characters
        return self._script.characters

    def _existing_scenes(self) -> Iterable[Scene]:
        if self._series is not None:
            return self._series.scenes
        return self._script.scenes

    def _existing_props(self) -> Iterable[Prop]:
        if self._series is not None:
            return self._series.props
        return self._script.props

    def _append_character(self, c: Character) -> None:
        if self._series is not None:
            self._series.characters.append(c)
        else:
            self._script.characters.append(c)

    def _append_scene(self, s: Scene) -> None:
        if self._series is not None:
            self._series.scenes.append(s)
        else:
            self._script.scenes.append(s)

    def _append_prop(self, p: Prop) -> None:
        if self._series is not None:
            self._series.props.append(p)
        else:
            self._script.props.append(p)


__all__ = ["EntityCatalog"]
