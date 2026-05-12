"""Tiny strategy registry. Keeps strategies discoverable by name
(``"full"`` / ``"incremental"``) without depending on import order."""
from __future__ import annotations

from typing import Callable, Dict, List, Type

from .strategies import ExtractionStrategy, FullExtraction, IncrementalExtraction

_REGISTRY: Dict[str, Type[ExtractionStrategy]] = {
    "full": FullExtraction,
    "incremental": IncrementalExtraction,
}


def register_strategy(name: str) -> Callable[[Type[ExtractionStrategy]], Type[ExtractionStrategy]]:
    """Decorator form: ``@register_strategy("custom")``."""

    def _wrap(cls: Type[ExtractionStrategy]) -> Type[ExtractionStrategy]:
        _REGISTRY[name] = cls
        return cls

    return _wrap


def get_strategy(name: str) -> ExtractionStrategy:
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown extraction strategy {name!r}. "
            f"Registered: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]()


def list_strategies() -> List[str]:
    return sorted(_REGISTRY)


__all__ = ["register_strategy", "get_strategy", "list_strategies"]
