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
from .base import BaseAction, ActionResult
from UI.SettingsConstant import SettingsKeys

logger = logging.getLogger(__name__)

class PrintMapAction(BaseAction):
    """Action to display maps and directions using Google Maps."""
    
    def __init__(self, maps_directory: Path, google_maps_api_key: str = None):
        """
        Initialize the map action with a directory for storing maps.
        
        :param maps_directory: Directory to store generated maps
        :param google_maps_api_key: Google Maps API key for authentication
        """
        self.maps_directory = maps_directory
        self.maps_directory.mkdir(parents=True, exist_ok=True)
        
        # Try to get API key from settings first
        if not google_maps_api_key:
            from UI.SettingsWindow import SettingsWindow
            settings = SettingsWindow()
            google_maps_api_key = settings.editable_settings.get(SettingsKeys.GOOGLE_MAPS_API_KEY.value)
            
        if not google_maps_api_key:
            google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        
        if not google_maps_api_key:
            # TODO: Add disable logic
            return
            
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
        if intent_name not in ["show_map", "show_directions", "find_location"]:
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
            
            if intent_name == "show_directions":
                # For directions, just show the destination marker since we don't know current location
                static_map_url = (
                    f"https://maps.googleapis.com/maps/api/staticmap?"
                    f"center={lat},{lng}&"
                    f"zoom=15&"
                    f"size=640x640&"
                    f"markers=color:red%7Clabel:D%7C{lat},{lng}&"
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
                
                data = {
                    "title": f"Route to {destination}",
                    "type": "map",
                    "clickable": True,
                    "click_url": str(map_path),
                    "has_action": True,
                    "auto_complete": False,
                    "action": self.complete_action,
                    "additional_info": {
                        "map_image_path": str(map_path)
                    }
                }

                data["action"] = lambda: self.complete_action(data)

                return ActionResult(
                    success=True,
                    message=f"Route to {destination}",
                    data=data
                )
            else:  # show_map or find_location
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
        # example of running a completion logic
        logger.info("Completing PrintMapAction")
        return True

    def _find_relevant_map(self, destination: str, transport_mode: str) -> Optional[Path]:
        """
        Find the most relevant map file based on destination.
        
        :param destination: Target medical facility
        :param transport_mode: Mode of transport (driving, transit, walking)
        :return: Path to the map file or None if not found
        """
        if not self.maps_directory.exists():
            logger.warning(f"Maps directory not found: {self.maps_directory}")
            return None
            
        # Try different combinations of search patterns
        patterns = [
            f"{destination}_{transport_mode}.*",
            f"{destination}.*",
            "default_map.*"
        ]
        
        for pattern in patterns:
            matches = list(self.maps_directory.glob(pattern))
            if matches:
                return matches[0]
        
        return None
    
    def _get_travel_time(self, destination: str, transport_mode: str) -> str:
        """Get estimated travel time to destination."""
        # In a real implementation, this would:
        # 1. Use a mapping service API (Google Maps, etc.)
        # 2. Consider current traffic conditions
        # 3. Account for time of day
        return "25-30 minutes"  # Placeholder
    
    def _get_landmarks(self, destination: str) -> List[str]:
        """Get key landmarks along the route."""
        # In a real implementation, this would:
        # 1. Load from a database of known landmarks
        # 2. Filter by relevance to the route
        return [
            "Turn right at Central Hospital",
            "Pass the Main Street intersection",
            "Look for the blue hospital sign"
        ]