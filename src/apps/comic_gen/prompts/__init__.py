"""Composable prompt builders for LLM stages.

Keeps the heavy system-prompt strings out of orchestration code
(``llm.py::ScriptProcessor``) so each builder can be tested and
recomposed independently.
"""
from .storyboard_builder import StoryboardPromptBuilder

__all__ = ["StoryboardPromptBuilder"]
