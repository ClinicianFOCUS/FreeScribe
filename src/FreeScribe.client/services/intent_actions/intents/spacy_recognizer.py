import logging
from typing import List, Dict, Optional, Pattern
import re
import spacy
from spacy.matcher import Matcher
from pydantic import BaseModel, Field, field_validator

from .base import BaseIntentRecognizer, Intent

logger = logging.getLogger(__name__)

class SpacyIntentPattern(BaseModel):
    """
    Pattern definition for SpaCy-based intent matching.
    
    :param intent_name: Name of the intent to match
    :type intent_name: str
    :param patterns: List of token patterns for the spaCy Matcher
    :type patterns: List[List[Dict[str, str]]]
    :param required_entities: Required entity types for this intent
    :type required_entities: List[str]
    :param confidence_weights: Weights for confidence calculation
    :type confidence_weights: Dict[str, float]
    :raises ValueError: If validation fails for any field
    """
    intent_name: str = Field(..., min_length=1, description="Name of the intent to match")
    patterns: List[List[Dict[str, str]]] = Field(..., min_length=1, description="List of token patterns for the spaCy Matcher")
    required_entities: List[str] = Field(default_factory=list, description="Required entity types for this intent")
    confidence_weights: Dict[str, float] = Field(
        default_factory=lambda: {"pattern_match": 0.6, "entity_match": 0.4},
        description="Weights for confidence calculation"
    )

    @field_validator("confidence_weights")
    @classmethod
    def validate_confidence_weights(cls, v):
        """
        Validate that confidence weights sum to 1.0.
        
        :param v: Dictionary of confidence weights
        :type v: Dict[str, float]
        :return: Validated confidence weights
        :rtype: Dict[str, float]
        :raises ValueError: If weights are invalid
        """
        if not v:
            raise ValueError("Confidence weights cannot be empty")
        
        total = sum(v.values())
        if not 0.99 <= total <= 1.01:  # Allow for small floating point errors
            raise ValueError("Confidence weights must sum to 1.0")
        
        if not all(0 <= w <= 1 for w in v.values()):
            raise ValueError("All confidence weights must be between 0 and 1")
        
        return v

    @field_validator("patterns")
    @classmethod
    def validate_patterns(cls, v):
        """
        Validate that patterns are properly formatted.
        
        :param v: List of patterns
        :type v: List[List[Dict[str, str]]]
        :return: Validated patterns
        :rtype: List[List[Dict[str, str]]]
        :raises ValueError: If patterns are invalid
        """
        if not v:
            raise ValueError("Patterns cannot be empty")
        
        for pattern in v:
            if not isinstance(pattern, list):
                raise ValueError("Each pattern must be a list of dictionaries")
            if not all(isinstance(token, dict) for token in pattern):
                raise ValueError("Each token in a pattern must be a dictionary")
            if not all(isinstance(key, str) and isinstance(value, str) 
                      for token in pattern for key, value in token.items()):
                raise ValueError("All pattern keys and values must be strings")
        
        return v

class SpacyIntentRecognizer(BaseIntentRecognizer):
    """
    SpaCy-based implementation of intent recognition.
    
    Uses pattern matching and entity recognition for medical intents.
    """
    
    def __init__(self, model_name: str = "en_core_web_md"):
        """
        Initialize the SpaCy recognizer.
        
        :param model_name: Name of the SpaCy model to use
        :type model_name: str
        """
        self.model_name = model_name
        self.nlp = None
        self.matcher = None
        self.patterns = [
            SpacyIntentPattern(
                intent_name="show_directions",
                patterns=[
                    [{"LOWER": "go"}, {"LOWER": "to"}],
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}],
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "go"}, {"LOWER": "to"}],
                    [{"LOWER": "directions"}, {"LOWER": "to"}],
                    [{"LOWER": "how"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}],
                    [{"LOWER": "where"}, {"LOWER": "is"}],
                    [{"LOWER": "find"}],
                    [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "to"}],
                    # New patterns for hospital-specific queries
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}, {"ENT_TYPE": "ORG"}],
                    [{"LOWER": "where"}, {"LOWER": "is"}, {"ENT_TYPE": "ORG"}],
                    [{"LOWER": "need"}, {"LOWER": "directions"}, {"LOWER": "to"}, {"ENT_TYPE": "ORG"}],
                    [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "how"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}, {"ENT_TYPE": "ORG"}],
                    [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LOWER": "main"}, {"LOWER": "entrance"}],
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}, {"ENT_TYPE": "ORG"}],
                    [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "the"}, {"LOWER": "way"}, {"LOWER": "to"}],
                    # Emergency room specific patterns
                    [{"LOWER": "get"}, {"LOWER": "to"}, {"LOWER": "emergency"}, {"LOWER": "room"}],
                    [{"LOWER": "find"}, {"LOWER": "emergency"}, {"LOWER": "room"}],
                    # Cardiac care specific patterns
                    [{"LOWER": "find"}, {"LEMMA": "cardiac"}, {"LEMMA": "care"}],
                    [{"LOWER": "get"}, {"LOWER": "to"}, {"LEMMA": "cardiac"}, {"LEMMA": "care"}],
                    # Cafeteria specific patterns
                    [{"LOWER": "way"}, {"LOWER": "to"}, {"LOWER": "cafeteria"}],
                    [{"LOWER": "find"}, {"LOWER": "cafeteria"}],
                    [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "cafeteria"}],
                    # New patterns for example texts
                    [{"LOWER": "need"}, {"LOWER": "directions"}, {"LOWER": "to"}],
                    [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "how"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}],
                    [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}],
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}],
                    [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "the"}, {"LOWER": "way"}, {"LOWER": "to"}],
                    # Department-specific patterns
                    [{"LOWER": "get"}, {"LOWER": "to"}, {"LOWER": "the"}, {"LEMMA": "department"}],
                    [{"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "department"}],
                    [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "department"}],
                    # Wing/entrance patterns
                    [{"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "wing"}],
                    [{"LOWER": "get"}, {"LOWER": "to"}, {"LOWER": "the"}, {"LEMMA": "wing"}],
                    [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "entrance"}],
                    [{"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "entrance"}],
                ],
                required_entities=[],  # Keep empty to allow matching without entities
                confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
            ),
            SpacyIntentPattern(
                intent_name="schedule_appointment",
                patterns=[
                    [{"LEMMA": "schedule"}, {"LOWER": "appointment"}],
                    [{"LEMMA": "book"}, {"LOWER": "appointment"}],
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "see"}],
                    # New appointment-related patterns
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}, {"ENT_TYPE": "ORG"}, {"LOWER": "for"}, {"LOWER": "appointment"}],
                    [{"LOWER": "appointment"}, {"LOWER": "at"}, {"ENT_TYPE": "TIME"}],
                ],
                required_entities=["TIME", "ORG"]
            ),
            # New pattern for location queries
            SpacyIntentPattern(
                intent_name="find_location",
                patterns=[
                    [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "cafeteria"}],
                    [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "entrance"}],
                    [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "wing"}],
                    [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "department"}],
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "cafeteria"}],
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "entrance"}],
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "wing"}],
                    [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "department"}],
                ],
                required_entities=[],  # No entity requirements for better matching
                confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}  # Focus on pattern matching
            )
        ]
    
    def add_pattern(self, pattern: SpacyIntentPattern) -> None:
        """
        Add a new pattern to the recognizer.
        
        :param pattern: Pattern to add
        :type pattern: SpacyIntentPattern
        """
        self.patterns.append(pattern)
        if self.matcher is not None:
            self.matcher.add(pattern.intent_name, pattern.patterns)
    
    def initialize(self) -> None:
        """
        Initialize SpaCy model and configure the matcher.
        
        :raises Exception: If initialization fails
        """
        try:
            if not spacy.util.is_package(self.model_name):
                logger.info(f"Downloading spaCy model {self.model_name}...")
                spacy.cli.download(self.model_name)
        except Exception as e:
            logger.exception(f"Failed to download spaCy model {str(e)}")
            return
        try:
            self.nlp = spacy.load(self.model_name)
            self.matcher = Matcher(self.nlp.vocab)
            
            # Add patterns to matcher
            for pattern in self.patterns:
                self.matcher.add(pattern.intent_name, pattern.patterns)
            
            logger.info("SpaCy Intent Recognizer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SpaCy Intent Recognizer: {e}")
            raise
    
    def _calculate_confidence(self, pattern: SpacyIntentPattern, doc, matches: List) -> float:
        """
        Calculate confidence score based on pattern matches and entity presence.
        
        :param pattern: Intent pattern definition
        :type pattern: SpacyIntentPattern
        :param doc: SpaCy Doc object
        :type doc: spacy.tokens.Doc
        :param matches: List of pattern matches
        :type matches: List[Tuple[int, int, int]]
        :return: Confidence score between 0 and 1
        :rtype: float
        """
        # If we have any matches, return high confidence
        if matches:
            logger.debug(f"Found matches for pattern {pattern.intent_name}, returning high confidence")
            return 1.0
            
        logger.debug(f"No matches found for pattern {pattern.intent_name}")
        return 0.0
    
    def _extract_parameters(self, doc) -> Dict[str, str]:
        """Extract parameters from recognized entities."""
        params = {
            "destination": "",
            "transport_mode": "driving",  # Default to driving
            "appointment_time": "",
            "patient_mobility": "",
            "additional_context": ""
        }
        
        for ent in doc.ents:
            if ent.label_ in ["LOCATION", "ORG", "GPE", "FAC"]:  # Support multiple location-like entities
                params["destination"] = ent.text
            elif ent.label_ == "TIME":
                params["appointment_time"] = ent.text
            elif ent.label_ == "TRANSPORT":  # Use TRANSPORT label for transport mode
                params["transport_mode"] = ent.text.lower()  # Normalize to lowercase
        
        return params
    
    def recognize_intent(self, text: str) -> List[Intent]:
        """
        Recognize medical intents from the conversation text using SpaCy.
        
        :param text: Transcribed conversation text
        :type text: str
        :return: List of recognized intents
        :rtype: List[Intent]
        """
        try:
            doc = self.nlp(text)
            recognized_intents = []
            
            logger.debug(f"Processing text: {text}")
            
            for pattern in self.patterns:
                # Get matches for this specific pattern
                matches = self.matcher(doc)
                matches = [m for m in matches if self.matcher.vocab.strings[m[0]] == pattern.intent_name]
                
                logger.debug(f"Found {len(matches)} matches for pattern {pattern.intent_name}")
                
                confidence = self._calculate_confidence(pattern, doc, matches)
                logger.debug(f"Calculated confidence: {confidence}")
                
                if confidence > 0.1:  # Lower confidence threshold since we're using simpler patterns
                    params = self._extract_parameters(doc)
                    logger.debug(f"Extracted parameters: {params}")
                    
                    intent = Intent(
                        name=pattern.intent_name,
                        confidence=confidence,
                        metadata={
                            "description": f"Recognized {pattern.intent_name} intent",
                            "required_action": pattern.intent_name,
                            "urgency_level": 2,  # Default urgency
                            "parameters": params
                        }
                    )
                    recognized_intents.append(intent)
                    logger.debug(f"Added intent: {intent}")
            
            return recognized_intents
            
        except Exception as e:
            logger.error(f"Error recognizing intent with SpaCy: {e}")
            return [] 