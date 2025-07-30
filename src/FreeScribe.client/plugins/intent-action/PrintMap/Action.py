"""
Map and directions action implementation using Google Maps API.
"""

import logging
from typing import Any, Dict, Optional, List
from pathlib import Path
import googlemaps
from datetime import datetime
import os
import requests
from services.intent_actions.actions.base import BaseAction, ActionResult
from UI.SettingsConstant import SettingsKeys

logger = logging.getLogger(__name__)

class PrintMapAction(BaseAction):
    """Action to display maps and directions using Google Maps."""
    
    def __init__(self, maps_directory: Optional[Path] = None, google_maps_api_key: str = None):
        """
        Initialize the map action with a directory for storing maps.
        
        :param maps_directory: Directory to store generated maps
        :param google_maps_api_key: Google Maps API key for authentication
        """
        if maps_directory is None:
            # Default to a maps directory in the plugin folder
            maps_directory = Path(__file__).parent / "maps"
            
        self.maps_directory = maps_directory
        self.maps_directory.mkdir(parents=True, exist_ok=True)
        
        # Try to get API key from settings first
        if not google_maps_api_key:
            try:
                from UI.SettingsWindow import SettingsWindow
                settings = SettingsWindow()
                google_maps_api_key = settings.editable_settings.get(SettingsKeys.GOOGLE_MAPS_API_KEY.value)
            except Exception as e:
                logger.warning(f"Could not load API key from settings: {e}")
            
        if not google_maps_api_key:
            google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        
        if not google_maps_api_key:
            logger.warning("No Google Maps API key found. Map functionality will be limited.")
            self.gmaps = None
        else:
            # Initialize Google Maps client
            self.gmaps = googlemaps.Client(key=google_maps_api_key)
        
        # Cache for storing location results
        self._location_cache = {}
        
        # Mock database of locations - in a real app this would come from a proper database
        self.locations = {
            "radiology": {
                "floor": 2,
                "wing": "East",
                "landmarks": ["Main Elevator", "Waiting Area", "Reception"],
                "directions": "Take the main elevator to the 2nd floor, turn right, and follow signs to Radiology"
            },
            "emergency": {
                "floor": 1,
                "wing": "North",
                "landmarks": ["Main Entrance", "Triage", "Ambulance Bay"],
                "directions": "Enter through the main entrance, Emergency is directly ahead"
            },
            "cafeteria": {
                "floor": 1,
                "wing": "West",
                "landmarks": ["Gift Shop", "Main Hallway", "Vending Machines"],
                "directions": "From the main entrance, follow the hallway past the gift shop"
            }
        }

    @property
    def action_id(self) -> str:
        """Get the unique identifier for this action."""
        return "print_map"

    @property
    def display_name(self) -> str:
        """Get the human-readable name for this action."""
        return "Print Map"

    @property
    def description(self) -> str:
        """Get the detailed description of what this action does."""
        return "Display maps and provide directions to hospital locations using Google Maps"

    def can_handle_intent(self, intent_name: str, metadata: Dict[str, Any]) -> bool:
        """Check if this action can handle the given intent."""
        if intent_name not in ["show_map", "find_location"]:
            return False
            
        # Check if we have a destination parameter
        params = metadata.get("parameters", {})
        destination = params.get("destination", "")
        return bool(destination)

    def execute(self, intent_name: str, metadata: Dict[str, Any]) -> ActionResult:
        """Execute the action for the given intent."""
        params = metadata.get("parameters", {})
        destination = params.get("destination", "")
        
        if not destination:
            return ActionResult(
                success=False,
                message="No destination specified.",
                data={"type": "error"},
            )
        
        if not self.gmaps:
            return ActionResult(
                success=False,
                message="Google Maps API key not configured.",
                data={"type": "error", "error": "No API key available"},
            )
            
        try:
            # Search Google Maps for the location
            search_query = destination
            try:
                places_result = self.gmaps.places(search_query)
            except Exception as e:
                logger.error(f"Google Maps API error: {str(e)}")
                return ActionResult(
                    success=False,
                    message=f"Error accessing Google Maps API: {str(e)}",
                    data={"type": "error", "error": str(e)},
                )

            if not places_result.get('results'):
                return ActionResult(
                    success=False,
                    message=f"Could not find {destination} on Google Maps.",
                    data={"type": "error"},
                )
            
            place = places_result['results'][0]
            
            # Generate static map
            map_filename = f"{destination.lower().replace(' ', '_')}_map.png"
            map_path = self.maps_directory / map_filename
            
            # Create static map URL based on intent
            lat = place['geometry']['location']['lat']
            lng = place['geometry']['location']['lng']
            
            # Create static map URL centered on location
            static_map_url = (
                f"https://maps.googleapis.com/maps/api/staticmap?"
                f"center={lat},{lng}&"
                f"zoom=16&"
                f"size=640x640&"
                f"markers=color:red%7C{lat},{lng}&"
                f"key={self.gmaps.key}"
            )
            
            # Download and save the map
            try:
                response = requests.get(static_map_url)
                response.raise_for_status()
                with open(map_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Successfully saved map to {map_path}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to download map: {str(e)}")
                return ActionResult(
                    success=False,
                    message=f"Failed to generate map image: {str(e)}",
                    data={"type": "error", "error": str(e)},
                )
            
            data={
                "title": f"{destination} Map",
                "type": "map",
                "clickable": True,
                "click_url": str(map_path),
                "has_action": True,
                "auto_complete": False,
                "action": self,
                "additional_info": {
                    "map_image_path": str(map_path)
                }
            }

            data["action"] = lambda: self.complete_action(data)

            
            return ActionResult(
                success=True,
                message=f"Click the map to view {destination}",
                data=data
            )
            
        except Exception as e:
            logger.error(f"Error executing map action: {str(e)}")
            return ActionResult(
                success=False,
                message=f"Unexpected error: {str(e)}",
                data={"type": "error", "error": str(e)},
            )

    def get_ui_data(self) -> Dict[str, Any]:
        """Get UI configuration for displaying results."""
        return {
            "icon": "🗺️",
            "color": "#4CAF50"
        }

    def complete_action(self, result_data: Dict[str, Any]) -> bool:
        """
        Complete the action - this is called when the user clicks "Complete Action" 
        or when auto_complete is triggered.
        
        :param result_data: The result data from the ActionResult
        :return: True if action was completed successfully, False otherwise
        """
        # Open the map file
        try:
            map_path = result_data.get("additional_info", {}).get("map_image_path")
            if map_path and os.path.exists(map_path):
                webbrowser.open(Path(map_path).absolute().as_uri())
                logger.info(f"Opened map file: {map_path}")
                return True
            else:
                logger.error("Map file not found")
                return False
        except Exception as e:
            logger.error(f"Error opening map file: {e}")
            return False

# Export the action for plugin loader
exported_actions = [PrintMapAction]