"""Automatic voice assignment for characters.

The audio stage needs every speaking character to have a ``voice_id``.
Asking the user to pick one for 10+ characters is a friction tax that
shows up on every new project; this package adds a one-shot
"auto-assign" path that runs a chain of rules with deterministic
ordering and falls back to a free voice from the available pool.

Manual overrides win: any character with ``locked=True`` or an existing
``voice_id`` is left untouched by :class:`LockedRule`.
"""
from .assigner import AssignContext, VoiceAssigner
from .rules import (
    DefaultPoolRule,
    LLMMatchRule,
    LockedRule,
    SeriesReuseRule,
    VoiceRule,
)

__all__ = [
    "AssignContext",
    "VoiceAssigner",
    "VoiceRule",
    "LockedRule",
    "SeriesReuseRule",
    "LLMMatchRule",
    "DefaultPoolRule",
]
