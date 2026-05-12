"""Voice-assignment rules — links in the Chain of Responsibility.

Each rule is a tiny, stateless class with a single method
``try_assign``. Returning ``None`` says "I don't know, ask the next
rule." Returning a voice id ends the chain for this character.

Order matters and is decided by the caller assembling the chain:

    LockedRule       → respect user/system pins first
    SeriesReuseRule  → inherit voice from same character in other episodes
    LLMMatchRule     → LLM picks best fit by gender / personality
    DefaultPoolRule  → final fallback so we never leave a speaker silent
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Set

from ..models import Character

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..llm import ScriptProcessor
    from .assigner import AssignContext

logger = logging.getLogger(__name__)


class VoiceRule(Protocol):
    """Single link in the assignment chain."""

    def try_assign(
        self,
        character: Character,
        available: List[Dict[str, Any]],
        used: Set[str],
        context: "AssignContext",
    ) -> Optional[str]:  # pragma: no cover - protocol
        ...


def _gender_match(voice_gender: Any, char_gender: Any) -> bool:
    """Soft gender match — unknown sides are treated as compatible."""
    if not voice_gender or not char_gender:
        return True
    vg = str(voice_gender).strip().lower()
    cg = str(char_gender).strip().lower()
    male_aliases = {"male", "m", "男", "男性"}
    female_aliases = {"female", "f", "女", "女性"}
    if vg in male_aliases and cg in male_aliases:
        return True
    if vg in female_aliases and cg in female_aliases:
        return True
    return vg == cg


# ── Rules ──────────────────────────────────────────────────────────────


class LockedRule:
    """Honour an already-set voice or a locked character.

    Two cases pin a character:

    * ``character.voice_id`` is non-empty → user has chosen already.
    * ``character.locked`` is True → user marked the character as
      "do not auto-touch", even if voice_id happens to be empty.

    In both cases this rule returns whatever voice_id is on the row
    (or empty string sentinel) so the chain stops and the caller's
    "skip blanks" check in :class:`~.assigner.VoiceAssigner` does the
    right thing.
    """

    def try_assign(self, character, available, used, context):
        if character.voice_id:
            return character.voice_id
        if character.locked:
            # Locked + blank voice = explicitly "don't auto-assign".
            # Return a sentinel that the caller treats as "skip".
            return None
        return None


class SeriesReuseRule:
    """Reuse the voice an identically-named character has in the Series.

    When a Series has 10 episodes and 叶墨 already has voice
    ``cosyvoice_v2_002`` in episode 1, episode 5's auto-assign should
    pick the same voice — otherwise the same character "sounds
    different" across episodes, which is jarring.
    """

    def try_assign(self, character, available, used, context):
        series = getattr(context, "series", None)
        if series is None:
            return None
        for other in series.characters:
            if other.id == character.id:
                continue
            if other.name == character.name and other.voice_id:
                # Reuse even if already used — same character, same voice
                # across episodes is the goal.
                return other.voice_id
        return None


class LLMMatchRule:
    """Ask the LLM to pick the best-matching voice from ``available``.

    Kept simple: one LLM call per character, prompt includes the
    character's gender/age/description and the *unused* voice pool.
    For Series episodes this is rare (SeriesReuseRule catches most),
    so the per-call cost is acceptable.

    Falls back to ``None`` (next rule) on any LLM error — picking a
    bad voice is worse than letting the default-pool rule handle it.
    """

    def __init__(self, llm: Optional["ScriptProcessor"] = None):
        self._llm = llm

    def try_assign(self, character, available, used, context):
        if self._llm is None or not self._llm.is_configured:
            return None
        candidates = [
            v for v in available
            if v.get("id") not in used and _gender_match(v.get("gender"), character.gender)
        ]
        if not candidates:
            return None
        try:
            return self._llm.match_voice_for_character(character, candidates)
        except Exception as e:
            logger.warning(
                "LLMMatchRule failed for character %s, falling through: %s",
                character.name, e,
            )
            return None


class DefaultPoolRule:
    """Pick the first unused voice with a compatible gender.

    The safety net — runs last so we never leave a speaking character
    without a voice. Prefers an unused voice; if everything is taken
    (more characters than voices), reuses the first gender-compatible
    voice rather than failing.
    """

    def try_assign(self, character, available, used, context):
        compatible = [
            v for v in available
            if _gender_match(v.get("gender"), character.gender)
        ]
        if not compatible:
            compatible = available  # last resort: ignore gender filter
        for v in compatible:
            vid = v.get("id")
            if vid and vid not in used:
                return vid
        # All voices taken — reuse the first one rather than return None
        for v in compatible:
            if v.get("id"):
                return v["id"]
        return None


__all__ = [
    "VoiceRule",
    "LockedRule",
    "SeriesReuseRule",
    "LLMMatchRule",
    "DefaultPoolRule",
]
