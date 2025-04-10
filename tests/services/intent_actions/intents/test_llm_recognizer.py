"""
Unit tests for the LLM intent recognizer.
"""

import pytest
from unittest.mock import Mock, patch
from pydantic import ValidationError
from services.intent_actions.intents.llm_recognizer import (
    MedicalIntentResult,
    LLMIntentRecognizer
)

@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    return {
        "intent_name": "test_intent",
        "description": "Test intent description",
        "required_action": "test_action",
        "urgency_level": 1,
        "relevant_parameters": {
            "destination": "test location",
            "transport_mode": "driving",
            "patient_mobility": "standard",
            "appointment_time": "",
            "additional_context": "test context"
        }
    }

@pytest.fixture
def mock_agent():
    """Create a mock pydantic_ai Agent."""
    mock_agent = Mock()
    mock_agent.run_sync.return_value = Mock(
        data=MedicalIntentResult(
            intent_name="test_intent",
            description="Test intent description",
            required_action="test_action",
            urgency_level=1,
            relevant_parameters={
                "destination": "test location",
                "transport_mode": "driving",
                "patient_mobility": "standard",
                "appointment_time": "",
                "additional_context": "test context"
            }
        )
    )
    return mock_agent

@pytest.fixture
def recognizer(mock_agent):
    """Create a test recognizer instance."""
    with patch("services.intent_actions.intents.llm_recognizer.Agent") as mock_agent_class:
        mock_agent_class.return_value = mock_agent
        recognizer = LLMIntentRecognizer(
            model_endpoint="http://localhost:11434",  # Default Ollama endpoint
            api_key=None  # Ollama doesn't require API key
        )
        recognizer.initialize()
        return recognizer

def test_medical_intent_result_creation(mock_llm_response):
    """Test MedicalIntentResult creation."""
    result = MedicalIntentResult(**mock_llm_response)
    
    assert result.intent_name == "test_intent"
    assert result.description == "Test intent description"
    assert result.required_action == "test_action"
    assert result.urgency_level == 1
    assert result.relevant_parameters == {
        "destination": "test location",
        "transport_mode": "driving",
        "patient_mobility": "standard",
        "appointment_time": "",
        "additional_context": "test context"
    }

def test_medical_intent_result_validation():
    """Test MedicalIntentResult validation."""
    # Test invalid urgency level
    with pytest.raises(ValidationError) as exc_info:
        MedicalIntentResult(
            intent_name="test_intent",
            description="test",
            required_action="test",
            urgency_level="invalid",  # Must be an integer
            relevant_parameters={
                "destination": "",
                "transport_mode": "driving",
                "patient_mobility": "",
                "appointment_time": "",
                "additional_context": ""
            }
        )
    assert "urgency_level" in str(exc_info.value)

def test_recognizer_initialization(recognizer):
    """Test LLMIntentRecognizer initialization."""
    assert recognizer.model_endpoint == "http://localhost:11434"
    assert recognizer.api_key is None
    assert recognizer.agent is not None

def test_recognizer_intent_recognition(recognizer, mock_llm_response):
    """Test intent recognition process."""
    intents = recognizer.recognize_intent("test text")
    
    assert len(intents) == 1
    assert intents[0].name == "test_intent"
    assert intents[0].confidence == 0.9  # LLM results have 0.9 confidence
    assert intents[0].metadata == {
        "description": "Test intent description",
        "required_action": "test_action",
        "urgency_level": 1,
        "parameters": {
            "destination": "test location",
            "transport_mode": "driving",
            "patient_mobility": "standard",
            "appointment_time": "",
            "additional_context": "test context"
        }
    }

def test_recognizer_llm_error(recognizer, mock_agent):
    """Test handling of LLM errors."""
    mock_agent.run_sync.side_effect = Exception("LLM error")
    
    intents = recognizer.recognize_intent("test text")
    assert len(intents) == 0

def test_recognizer_invalid_response(recognizer, mock_agent):
    """Test handling of invalid LLM response."""
    mock_agent.run_sync.side_effect = ValueError("Invalid response")
    
    intents = recognizer.recognize_intent("test text")
    assert len(intents) == 0

def test_recognizer_missing_fields(recognizer, mock_agent):
    """Test handling of LLM response with missing fields."""
    mock_agent.run_sync.side_effect = ValueError("Missing required fields")
    
    intents = recognizer.recognize_intent("test text")
    assert len(intents) == 0 