from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ActionResult(BaseModel):
    """
    Result of an action execution.
    
    :param success: Whether the action was successful
    :param message: Human-readable message about the result
    :param data: Additional data returned by the action
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class BaseAction(ABC):
    """
    Base class for all action plugins.
    
    Actions are triggered in response to recognized intents and perform
    specific tasks like scheduling tests or showing medical information.
    """
    
    @property
    @abstractmethod
    def action_id(self) -> str:
        """
        Unique identifier for the action.
        """
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable name for the action.
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Detailed description of what the action does.
        """
        pass
    
    @abstractmethod
    def can_handle_intent(self, intent_name: str, metadata: Dict[str, Any]) -> bool:
        """
        Check if this action can handle the given intent.
        
        :param intent_name: Name of the recognized intent
        :param metadata: Additional data from the intent
        :return: True if this action can handle the intent
        """
        pass
    
    @abstractmethod
    def execute(self, intent_name: str, metadata: Dict[str, Any]) -> ActionResult:
        """
        Execute the action based on the intent.
        
        :param intent_name: Name of the recognized intent
        :param metadata: Additional data from the intent
        :return: Result of the action execution
        """
        pass
    
    @abstractmethod
    def get_ui_data(self) -> Dict[str, Any]:
        """
        Get data needed to render the action in the UI.
        
        :return: Dictionary containing UI-related data (icon, color, etc.)
        """
        pass 