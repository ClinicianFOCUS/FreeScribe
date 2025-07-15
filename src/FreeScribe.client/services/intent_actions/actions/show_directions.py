"""
Action to generate directions URL for display in the UI.
"""

import logging
from typing import Any, Dict
from urllib.parse import quote_plus
from .base import BaseAction, ActionResult

logger = logging.getLogger(__name__)

class ShowDirectionsAction(BaseAction):
    """Action to show directions using Google Maps."""
    
    def __init__(self):
        """Initialize the directions action."""
        super().__init__()
    
    @property
    def action_id(self) -> str:
        """Get the unique identifier for this action."""
        return "show_directions"

    @property
    def display_name(self) -> str:
        """Get the human-readable name for this action."""
        return "Show Directions"

    @property
    def description(self) -> str:
        """Get the detailed description of what this action does."""
        return "Show directions to your destination using Google Maps"

    def can_handle_intent(self, intent_name: str, metadata: Dict[str, Any]) -> bool:
        """
        Check if this action can handle the given intent.
        
        :param intent_name: Name of the intent to check
        :param metadata: Intent metadata containing parameters
        :return: True if this action can handle the intent
        """
        if intent_name != "show_directions":
            return False
            
        # Check if we have required parameters
        params = metadata.get("parameters", {})
        return bool(params.get("destination"))

    def execute(self, intent_name: str, metadata: Dict[str, Any]) -> ActionResult:
        """
        Execute the action for the given intent.
        
        :param intent_name: Name of the intent to execute
        :param metadata: Intent metadata containing parameters
        :return: Result of the action execution
        """
        params = metadata.get("parameters", {})
        destination = params.get("destination", "")
        transport_mode = params.get("transport_mode", "driving")
        
        if not destination:
            return ActionResult(
                success=False,
                message="No destination specified.",
                data={}
            )
            
        try:
            # Create Google Maps URL
            url = (
                "https://www.google.com/maps/dir/?api=1"
                f"&origin=current+location"
                f"&destination={quote_plus(destination)}"
                f"&travelmode={transport_mode}"
            )
            
            transport_icon = self._get_transport_mode_icon(transport_mode)
            
            return ActionResult(
                success=True,
                message=f"{transport_icon} Directions to {destination}",
                data={
                    "title": f"Directions to {destination}",
                    "type": "directions",
                    "url": url,
                    "destination": destination,
                    "transport_mode": transport_mode,
                    "transport_mode_icon": transport_icon,
                    "clickable": True,
                    "click_url": url,  # This is what the UI will use
                    "has_action": True,
                    "auto_complete": False,
                    "action": self
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating directions URL: {str(e)}")
            return ActionResult(
                success=False,
                message="Failed to generate directions.",
                data={"error": str(e)}
            )

    def complete_action(self, result_data: Dict[str, Any]) -> bool:
        """
        Complete the action with the provided result data.
        
        :param result_data: Data returned from the action execution
        :return: True if the action was completed successfully
        """
        # This action does not require any additional completion logic
        logger.info("ShowDirectionsAction completed successfully.")
        return True

    def get_ui_data(self) -> Dict[str, Any]:
        """Get UI configuration for displaying results."""
        return {
            "icon": "🧭",
            "color": "#2196F3"
        }
        
    def _get_transport_mode_icon(self, mode: str) -> str:
        """Get an icon representing the transport mode."""
        icons = {
            "driving": "🚗",
            "walking": "🚶",
            "bicycling": "🚲",
            "transit": "🚌"
        }
        return icons.get(mode, "🚗") 