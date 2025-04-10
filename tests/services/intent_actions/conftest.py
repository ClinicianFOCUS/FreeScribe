"""
Shared fixtures for intent actions tests.
"""

import pytest
from pathlib import Path
from typing import Dict, Any

@pytest.fixture
def sample_intent_metadata() -> Dict[str, Any]:
    """Create sample intent metadata for testing."""
    return {
        "destination": "radiology",
        "transport_mode": "driving",
        "user_location": {"lat": 37.7749, "lng": -122.4194}
    }

@pytest.fixture
def sample_google_places_response() -> Dict[str, Any]:
    """Create sample Google Places API response."""
    return {
        'results': [{
            'geometry': {'location': {'lat': 37.7749, 'lng': -122.4194}},
            'place_id': 'test_place_id',
            'formatted_address': '123 Test St',
            'name': 'Test Hospital',
            'rating': 4.5,
            'types': ['hospital', 'health']
        }]
    }

@pytest.fixture
def sample_google_directions_response() -> Dict[str, Any]:
    """Create sample Google Directions API response."""
    return [{
        'legs': [{
            'duration': {'text': '30 mins', 'value': 1800},
            'distance': {'text': '5 km', 'value': 5000},
            'steps': [
                {'html_instructions': 'Turn right'},
                {'html_instructions': 'Continue straight'}
            ]
        }]
    }] 