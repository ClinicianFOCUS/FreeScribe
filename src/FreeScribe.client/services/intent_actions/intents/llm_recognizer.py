"""
LLM-based intent recognition implementation.
"""

import logging
from typing import List, Optional, Dict
from pydantic import BaseModel
from pydantic_ai import Agent

from .base import BaseIntentRecognizer, Intent

logger = logging.getLogger(__name__)

class MedicalIntentResult(BaseModel):
    """
    Medical intent model for LLM-based recognition.
    
    :param intent_name: Name of the recognized intent
    :param description: Detailed description of the intent
    :param required_action: Type of action required
    :param urgency_level: Level of urgency (1-5)
    :param relevant_parameters: Additional parameters extracted from the text
    """
    intent_name: str
    description: str
    required_action: str
    urgency_level: int
    relevant_parameters: Dict[str, str] = {
        "destination": "",  # Target medical facility
        "transport_mode": "driving",  # Mode of transport
        "patient_mobility": "",  # Any mobility considerations
        "appointment_time": "",  # If there's a specific appointment time
        "additional_context": ""  # Any other relevant context
    }

class LLMIntentRecognizer(BaseIntentRecognizer):
    """
    LLM-based implementation of intent recognition.
    
    Uses PydanticAI to structure the LLM output into actionable intents.
    """
    
    def __init__(self, model_endpoint: str = "http://localhost:11434", api_key: Optional[str] = None):
        """
        Initialize the LLM recognizer.
        
        :param model_endpoint: URL of the self-hosted Ollama API (default: http://localhost:11434)
        :param api_key: Optional API key for authentication (not used for Ollama)
        """
        self.model_endpoint = model_endpoint
        self.api_key = api_key
        self.agent = Agent(
            "gemma-2-2b-it-Q8_0",  # Using Gemma 2B model
            result_type=MedicalIntentResult,
            system_prompt="""You are a medical intent recognition system.
            Analyze the conversation between physician and patient to identify key intents,
            particularly focusing on referrals and directions to other medical facilities.
            
            When directions or locations are mentioned:
            - Identify the destination facility (hospital, clinic, lab, etc.)
            - Note any transportation requirements or preferences
            - Consider patient mobility needs
            - Look for timing constraints (appointments, opening hours)
            
            Example:
            Input: "You'll need to go to Central Hospital for the MRI. It's about 20 minutes from here."
            Output: {
                "intent_name": "show_directions",
                "description": "Show route to Central Hospital for MRI appointment",
                "required_action": "display_route",
                "urgency_level": 2,
                "relevant_parameters": {
                    "destination": "Central Hospital",
                    "transport_mode": "driving",
                    "patient_mobility": "standard",
                    "appointment_time": "",
                    "additional_context": "MRI appointment"
                }
            }"""
        )
    
    def initialize(self) -> None:
        """Initialize the LLM connection and verify the endpoint."""
        try:
            # Test connection with a simple prompt
            test_intent = self.agent.run_sync(
                "test connection",
                api_base=self.model_endpoint,
                api_key=self.api_key
            )
            logger.info("LLM Intent Recognizer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Intent Recognizer: {e}")
            raise
    
    def recognize_intent(self, text: str) -> List[Intent]:
        """
        Recognize medical intents from the conversation text.
        
        :param text: Transcribed conversation text
        :return: List of recognized intents
        """
        try:
            result = self.agent.run_sync(
                text,
                api_base=self.model_endpoint,
                api_key=self.api_key
            )
            
            # Convert MedicalIntentResult to base Intent
            return [Intent(
                name=result.data.intent_name,
                confidence=0.9,  # LLM doesn't provide confidence, using high default
                metadata={
                    "description": result.data.description,
                    "required_action": result.data.required_action,
                    "urgency_level": result.data.urgency_level,
                    "parameters": result.data.relevant_parameters
                }
            )]
        except Exception as e:
            logger.error(f"Error recognizing intent: {e}")
            return [] 