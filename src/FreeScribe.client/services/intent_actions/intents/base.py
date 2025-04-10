"""
Base classes for intent recognition.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator

class Intent(BaseModel):
    """
    Base class for intent models.
    
    :param name: Name of the intent
    :type name: str
    :param confidence: Confidence score between 0 and 1
    :type confidence: float
    :param metadata: Additional metadata about the intent
    :type metadata: Dict[str, Any]
    """
    name: str = Field(..., min_length=1, description="Name of the intent")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score between 0 and 1")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the intent")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """
        Validate that the name is not empty.
        
        :param v: Name to validate
        :type v: str
        :return: Validated name
        :rtype: str
        :raises ValueError: If name is empty
        """
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        """
        Validate that confidence is between 0 and 1.
        
        :param v: Confidence to validate
        :type v: float
        :return: Validated confidence
        :rtype: float
        :raises ValueError: If confidence is invalid
        """
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v

class BaseIntentRecognizer(ABC):
    """
    Abstract base class for intent recognizers.
    
    All intent recognizers must implement this interface.
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the recognizer.
        
        This method should be called before using the recognizer.
        """
        pass
    
    @abstractmethod
    def recognize_intent(self, text: str) -> List[Intent]:
        """
        Recognize intents from text.
        
        :param text: Text to analyze
        :type text: str
        :return: List of recognized intents
        :rtype: List[Intent]
        """
        pass
