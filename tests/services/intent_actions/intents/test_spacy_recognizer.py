"""
Tests for SpaCy-based intent recognition.
"""

import pytest
from pydantic import ValidationError
import spacy
from unittest.mock import patch, MagicMock

from services.intent_actions.intents.spacy_recognizer import SpacyIntentPattern, SpacyIntentRecognizer

@pytest.fixture
def mock_nlp():
    """Create a mock SpaCy NLP model."""
    mock = MagicMock()
    mock.vocab = spacy.blank("en").vocab
    return mock

@pytest.fixture
def test_pattern():
    """Create a test intent pattern."""
    return SpacyIntentPattern(
        intent_name="test_intent",
        patterns=[[{"LOWER": "test"}, {"LOWER": "pattern"}]],
        required_entities=["LOCATION"],
        confidence_weights={"pattern_match": 0.6, "entity_match": 0.4}
    )

@pytest.fixture
def recognizer(mock_nlp):
    """Create a SpaCy recognizer with mocked model."""
    with patch("spacy.load", return_value=mock_nlp):
        recognizer = SpacyIntentRecognizer()
        recognizer.initialize()
        return recognizer

def test_pattern_creation():
    """Test creating a valid pattern."""
    pattern = SpacyIntentPattern(
        intent_name="test_intent",
        patterns=[[{"LOWER": "test"}]],
        required_entities=["LOCATION"],
        confidence_weights={"pattern_match": 0.6, "entity_match": 0.4}
    )
    assert pattern.intent_name == "test_intent"
    assert len(pattern.patterns) == 1
    assert pattern.required_entities == ["LOCATION"]
    assert pattern.confidence_weights == {"pattern_match": 0.6, "entity_match": 0.4}

def test_pattern_validation():
    """Test pattern validation rules."""
    # Test empty intent name
    with pytest.raises(ValidationError) as exc_info:
        SpacyIntentPattern(
            intent_name="",
            patterns=[[{"LOWER": "test"}]]
        )
    assert "intent_name" in str(exc_info.value)

    # Test empty patterns
    with pytest.raises(ValidationError) as exc_info:
        SpacyIntentPattern(
            intent_name="test_intent",
            patterns=[]
        )
    assert "patterns" in str(exc_info.value)

    # Test invalid pattern format
    with pytest.raises(ValidationError) as exc_info:
        SpacyIntentPattern(
            intent_name="test_intent",
            patterns=[{"invalid": "format"}]
        )
    assert "patterns" in str(exc_info.value)

    # Test invalid confidence weights
    with pytest.raises(ValidationError) as exc_info:
        SpacyIntentPattern(
            intent_name="test_intent",
            patterns=[[{"LOWER": "test"}]],
            confidence_weights={"pattern_match": 0.7, "entity_match": 0.4}
        )
    assert "confidence_weights" in str(exc_info.value)

def test_recognizer_initialization(recognizer):
    """Test recognizer initialization."""
    assert recognizer.nlp is not None
    assert recognizer.matcher is not None
    assert len(recognizer.patterns) > 0

def test_add_pattern(recognizer):
    """Test adding a new pattern to the recognizer."""
    pattern = SpacyIntentPattern(
        intent_name="new_intent",
        patterns=[[{"LOWER": "new"}]]
    )
    recognizer.patterns.append(pattern)
    recognizer.matcher.add(pattern.intent_name, pattern.patterns)
    assert len(recognizer.patterns) > 1
    assert pattern.intent_name in recognizer.matcher

def test_calculate_confidence(recognizer):
    """Test confidence calculation."""
    pattern = SpacyIntentPattern(
        intent_name="test_intent",
        patterns=[[{"LOWER": "test"}]],
        required_entities=["LOCATION"],
        confidence_weights={"pattern_match": 0.6, "entity_match": 0.4}
    )
    
    doc = MagicMock()
    doc.ents = [MagicMock(label_="LOCATION")]
    matches = [(0, 1, 0.8)]  # One match with high confidence
    
    confidence = recognizer._calculate_confidence(pattern, doc, matches)
    assert confidence == 1.0  # Full confidence when both pattern and entity match

def test_extract_parameters(recognizer):
    """Test parameter extraction from entities."""
    doc = MagicMock()
    doc.ents = [
        MagicMock(label_="LOCATION", text="Test Hospital"),
        MagicMock(label_="TIME", text="tomorrow"),
        MagicMock(label_="TRANSPORT", text="ambulance")
    ]
    
    params = recognizer._extract_parameters(doc)
    expected_params = {
        "destination": "Test Hospital",
        "transport_mode": "ambulance",
        "appointment_time": "tomorrow",
        "patient_mobility": "",
        "additional_context": ""
    }
    assert params == expected_params

def test_extract_parameters_with_org(recognizer):
    """Test parameter extraction with ORG entity."""
    doc = MagicMock()
    doc.ents = [
        MagicMock(label_="ORG", text="City Hospital"),
        MagicMock(label_="TIME", text="2 PM")
    ]
    
    params = recognizer._extract_parameters(doc)
    expected_params = {
        "destination": "City Hospital",
        "transport_mode": "driving",  # Default value
        "appointment_time": "2 PM",
        "patient_mobility": "",
        "additional_context": ""
    }
    assert params == expected_params

def test_extract_parameters_with_gpe(recognizer):
    """Test parameter extraction with GPE entity."""
    doc = MagicMock()
    doc.ents = [
        MagicMock(label_="GPE", text="Downtown Medical Center")
    ]
    
    params = recognizer._extract_parameters(doc)
    expected_params = {
        "destination": "Downtown Medical Center",
        "transport_mode": "driving",  # Default value
        "appointment_time": "",
        "patient_mobility": "",
        "additional_context": ""
    }
    assert params == expected_params

def test_extract_parameters_empty(recognizer):
    """Test parameter extraction with no entities."""
    doc = MagicMock()
    doc.ents = []
    
    params = recognizer._extract_parameters(doc)
    expected_params = {
        "destination": "",
        "transport_mode": "driving",  # Default value
        "appointment_time": "",
        "patient_mobility": "",
        "additional_context": ""
    }
    assert params == expected_params

def test_recognize_intent(recognizer):
    """Test intent recognition."""
    text = "I need to go to Test Hospital tomorrow"
    intents = recognizer.recognize_intent(text)
    assert isinstance(intents, list)
    if intents:
        intent = intents[0]
        assert intent.name in [p.intent_name for p in recognizer.patterns]
        assert 0 <= intent.confidence <= 1
        assert "parameters" in intent.metadata

def test_no_matches(recognizer):
    """Test handling of text with no matching patterns."""
    text = "This is a completely unrelated text"
    intents = recognizer.recognize_intent(text)
    assert isinstance(intents, list)
    assert len(intents) == 0

def test_recognizer_parameter_extraction(recognizer, test_pattern):
    """Test parameter extraction from text."""
    mock_doc = MagicMock()
    mock_ent = MagicMock()
    mock_ent.label_ = "LOCATION"
    mock_ent.text = "test location"
    mock_doc.ents = [mock_ent]
    
    params = recognizer._extract_parameters(mock_doc)
    expected_params = {
        "destination": "test location",
        "transport_mode": "driving",
        "appointment_time": "",
        "patient_mobility": "",
        "additional_context": ""
    }
    assert params == expected_params

def test_recognizer_intent_recognition(recognizer, test_pattern, mock_nlp):
    """Test intent recognition process."""
    # Setup mock doc
    mock_doc = MagicMock()
    mock_doc.text = "test pattern at test location"
    mock_doc.ents = [MagicMock(label_="LOCATION", text="test location")]
    mock_nlp.return_value = mock_doc
    
    # Mock matcher to return matches
    mock_match = (0, 1, 0.8)  # (match_id, start, end)
    recognizer.matcher = MagicMock()
    recognizer.matcher.return_value = [mock_match]
    recognizer.matcher.vocab.strings = {0: "test_intent"}
    
    # Add pattern and recognize
    recognizer.add_pattern(test_pattern)
    intents = recognizer.recognize_intent("test pattern at test location")
    
    assert len(intents) == 1
    assert intents[0].name == "test_intent"
    assert intents[0].confidence == 1.0  # Both pattern and entity match
    expected_params = {
        "destination": "test location",
        "transport_mode": "driving",
        "appointment_time": "",
        "patient_mobility": "",
        "additional_context": ""
    }
    assert intents[0].metadata["parameters"] == expected_params

def test_recognizer_no_match(recognizer, test_pattern, mock_nlp):
    """Test when no pattern matches."""
    mock_doc = MagicMock()
    mock_doc.text = "unrelated text"
    mock_doc.ents = []
    mock_nlp.return_value = mock_doc
    
    recognizer.add_pattern(test_pattern)
    intents = recognizer.recognize_intent("unrelated text")
    
    assert len(intents) == 0 