"""Entity extraction layer.

Splits "find characters/scenes/props in this script" into three concerns:

* :mod:`catalog` — adapter over ``Series``/``Script`` that the extractor
  treats as a read-write entity store (Repository pattern).
* :mod:`dedup` — per-entity ``MatchSpec`` rules deciding whether a
  candidate dict refers to an already-known entity (Specification).
* :mod:`strategies` — pluggable ``ExtractionStrategy`` implementations
  (Strategy + Registry): ``"full"`` re-extracts everything, ``"incremental"``
  only fills gaps and is the recommended path for Series episodes.

The public surface is intentionally tiny: callers usually only need
:func:`get_strategy` plus :class:`EntityCatalog`.
"""
from .catalog import EntityCatalog
from .dedup import CharacterMatchSpec, MatchSpec, PropMatchSpec, SceneMatchSpec
from .registry import get_strategy, list_strategies, register_strategy
from .strategies import (
    ExtractionResult,
    ExtractionStrategy,
    FullExtraction,
    IncrementalExtraction,
)

__all__ = [
    "EntityCatalog",
    "ExtractionResult",
    "ExtractionStrategy",
    "FullExtraction",
    "IncrementalExtraction",
    "MatchSpec",
    "CharacterMatchSpec",
    "SceneMatchSpec",
    "PropMatchSpec",
    "get_strategy",
    "list_strategies",
    "register_strategy",
]
