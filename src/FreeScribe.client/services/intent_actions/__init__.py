"""
Intent recognition and action system for FreeScribe.

This module provides a unified interface for intent recognition and action execution
in the FreeScribe medical transcription system.
"""

from .intents import (
    Intent,
    BaseIntentRecognizer,
    LLMIntentRecognizer,
    MedicalIntentResult
)
from .actions import (
    BaseAction,
    ActionResult
)


__all__ = [
    'Intent',
    'ActionResult',
    'BaseIntentRecognizer',
    'BaseAction',
    'LLMIntentRecognizer',
    'MedicalIntentResult'
] 