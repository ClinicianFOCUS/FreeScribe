"""
Google Maps service for handling API key loading, place search, and static map generation.
"""

import os
import requests
import googlemaps
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class GoogleMapsService:
    """Service for interacting with Google Maps API."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Google Maps service.
        
        :param api_key: Google Maps API key (optional, will try environment variable if not provided)
        :raises ValueError: If no API key is available
        """
        key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not key:
            raise ValueError("Google Maps API key is missing")
        
        self.client = googlemaps.Client(key=key)
        
    def find_place(self, query: str) -> Dict[str, float]:
        """
        Find a place using Google Maps Places API.
        
        :param query: Search query for the place
        :return: Dictionary with lat and lng of the place
        :raises LookupError: If place is not found
        :raises Exception: If API request fails
        """
        try:
            resp = self.client.places(query)
            results = resp.get("results")
            if not results:
                raise LookupError(f"'{query}' not found on Google Maps")
            
            location = results[0]["geometry"]["location"]
            return {"lat": location["lat"], "lng": location["lng"]}
        except googlemaps.exceptions.ApiError as e:
            logger.error(f"Google Maps API error: {e}")
            raise Exception(f"Google Maps API error: {e}")
        except Exception as e:
            logger.error(f"Error finding place '{query}': {e}")
            raise
    
    def get_static_map_bytes(self, lat: float, lng: float, size="640x640", zoom=16) -> bytes:
        """
        Get static map image bytes from Google Maps Static API.
        
        :param lat: Latitude of the location
        :param lng: Longitude of the location  
        :param size: Size of the map image (default: "640x640")
        :param zoom: Zoom level (default: 16)
        :return: Raw bytes of the map image
        :raises requests.RequestException: If the request fails
        """
        url = (
            "https://maps.googleapis.com/maps/api/staticmap?"
            f"center={lat},{lng}&zoom={zoom}&size={size}"
            f"&markers=color:red%7C{lat},{lng}&key={self.client.key}"
        )
        
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as e:
            logger.error(f"Failed to get static map: {e}")
            raise