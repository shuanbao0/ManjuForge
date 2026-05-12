"""``VoiceAssigner`` — Chain of Responsibility runner.

Each :class:`~.rules.VoiceRule` in the chain gets a shot at picking a
voice for the current character. The first non-``None`` return wins;
later rules don't see that character. Rules are stateless — the runner
threads the mutable "already used voices" set through each call so
rules can avoid collisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from ..models import Character, Series

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .rules import VoiceRule


@dataclass
class AssignContext:
    """Per-run context shared with every rule.

    Carrying this in a single dataclass means adding new signal
    sources (e.g. user-set genre, regional voice preferences) later
    doesn't change every rule's signature.
    """

    series: Optional[Series] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class VoiceAssigner:
    """Run a chain of :class:`VoiceRule` over a list of characters.

    Usage::

        assigner = VoiceAssigner([LockedRule(), SeriesReuseRule(),
                                  LLMMatchRule(llm), DefaultPoolRule()])
        mapping = assigner.assign_all(script.characters, available, context)
        for ch in script.characters:
            if vid := mapping.get(ch.id):
                ch.voice_id = vid
                ch.voice_name = voice_name_of(vid, available)

    The runner does not mutate ``Character`` objects directly; that
    keeps it safe to call from inside transactions / preview flows.
    """

    def __init__(self, rules: List["VoiceRule"]):
        self._rules = rules

    def assign_all(
        self,
        characters: List[Character],
        available: List[Dict[str, Any]],
        context: AssignContext,
    ) -> Dict[str, str]:
        used: Set[str] = {c.voice_id for c in characters if c.voice_id}
        out: Dict[str, str] = {}
        for ch in characters:
            for rule in self._rules:
                voice_id = rule.try_assign(ch, available, used, context)
                if voice_id:
                    out[ch.id] = voice_id
                    used.add(voice_id)
                    break
        return out


__all__ = ["AssignContext", "VoiceAssigner"]
