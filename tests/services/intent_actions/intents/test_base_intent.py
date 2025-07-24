"""
Unit tests for the base intent classes.
"""

import pytest
from pydantic import ValidationError
from typing import List
from services.intent_actions.intents.base import Intent, BaseIntentRecognizer

class TestIntentRecognizer(BaseIntentRecognizer):
    """Test implementation of BaseIntentRecognizer."""
    
    def initialize(self) -> None:
        """Initialize the test recognizer."""
        pass
    
    def recognize_intent(self, text: str) -> List[Intent]:
        """Recognize intents from text."""
        return []

@pytest.fixture
def test_intent():
    """Create a test intent instance."""
    return Intent(
        name="test_intent",
        confidence=0.8,
        metadata={"test": "value"}
    )

@pytest.fixture
def test_recognizer():
    """Create a test recognizer instance."""
    return TestIntentRecognizer()

def test_intent_creation(test_intent):
    """Test Intent creation."""
    assert test_intent.name == "test_intent"
    assert test_intent.confidence == 0.8
    assert test_intent.metadata == {"test": "value"}

def test_intent_validation():
    """Test Intent validation."""
    # Test invalid confidence
    with pytest.raises(ValidationError) as exc_info:
        Intent(
            name="invalid_intent",
            confidence=1.5,  # Invalid confidence value
            metadata={}
        )
    assert "confidence" in str(exc_info.value)
    assert "less than or equal to 1" in str(exc_info.value)
    
    # Test empty name
    with pytest.raises(ValidationError) as exc_info:
        Intent(
            name="",  # Empty name
            confidence=0.8,
            metadata={}
        )
    assert "name" in str(exc_info.value)
    assert "String should have at least 1 character" in str(exc_info.value)

def test_base_recognizer_interface(test_recognizer):
    """Test BaseIntentRecognizer interface implementation."""
    # Test initialization
    test_recognizer.initialize()
    # Test intent recognition
    intents = test_recognizer.recognize_intent("test text")
    assert isinstance(intents, list)

def test_intent_metadata_edge_cases():
    """Test edge cases for the metadata field in Intent."""
    # Metadata missing (should default to empty dict or raise error depending on model)
    intent = Intent(
        name="meta_missing",
        confidence=0.5
    )
    assert hasattr(intent, "metadata")
    assert isinstance(intent.metadata, dict)
    # Metadata set to None (should raise ValidationError)
    with pytest.raises(ValidationError) as exc_info:
        Intent(
            name="meta_none",
            confidence=0.5,
            metadata=None
        )
    assert "metadata" in str(exc_info.value)
    # Metadata with unexpected type (e.g., list)
    with pytest.raises(ValidationError) as exc_info:
        Intent(
            name="meta_wrong_type",
            confidence=0.5,
            metadata=["not", "a", "dict"]
        )
    assert "metadata" in str(exc_info.value)

def test_base_recognizer_abstract_methods():
    """Test that BaseIntentRecognizer cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseIntentRecognizer() 