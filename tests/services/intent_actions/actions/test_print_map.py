"""
Unit tests for the print map action.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any
from services.intent_actions.actions.print_map import PrintMapAction
from services.intent_actions.actions.base import ActionResult
from UI.SettingsConstant import SettingsKeys

@pytest.fixture
def mock_gmaps():
    """Create a mock Google Maps client."""
    with patch('googlemaps.Client') as mock:
        client = Mock()
        client.key = "fake_api_key"
        mock.return_value = client
        yield client

@pytest.fixture
def mock_requests():
    """Create a mock requests module."""
    with patch('requests.get') as mock:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_data'
        mock.return_value = mock_response
        yield mock

@pytest.fixture
def maps_dir(tmp_path):
    """Create a temporary directory for maps."""
    maps_dir = tmp_path / "hospital_maps"
    maps_dir.mkdir()
    return maps_dir

@pytest.fixture
def mock_settings():
    """Mock settings to provide API key."""
    with patch('UI.SettingsWindow.SettingsWindow') as mock:
        settings_instance = Mock()
        settings_instance.editable_settings = {SettingsKeys.GOOGLE_MAPS_API_KEY.value: "fake_api_key"}
        mock.return_value = settings_instance
        yield mock

@pytest.fixture
def print_map_action(maps_dir, mock_gmaps, mock_settings):
    """Create a PrintMapAction instance with mocked dependencies."""
    return PrintMapAction(maps_dir)

@pytest.fixture
def sample_place_result():
    """Create a sample Google Places API result."""
    return {
        'results': [{
            'geometry': {'location': {'lat': 37.7749, 'lng': -122.4194}},
            'place_id': 'test_place_id',
            'formatted_address': '123 Test St'
        }]
    }

def test_action_properties(print_map_action):
    """Test that action properties return correct values."""
    assert print_map_action.action_id == "print_map"
    assert print_map_action.display_name == "Print Map"
    assert "Google Maps" in print_map_action.description

def test_can_handle_intent_valid_show_map(print_map_action):
    """Test show_map intent handling."""
    assert print_map_action.can_handle_intent("show_map", {"parameters": {"destination": "radiology"}}) is True

def test_can_handle_intent_valid_show_directions(print_map_action):
    """Test show_directions intent handling."""
    assert print_map_action.can_handle_intent("show_directions", {"parameters": {"destination": "emergency"}}) is True

def test_can_handle_intent_valid_find_location(print_map_action):
    """Test find_location intent handling."""
    assert print_map_action.can_handle_intent("find_location", {"parameters": {"destination": "cafeteria"}}) is True

def test_can_handle_intent_invalid_intent(print_map_action):
    """Test invalid intent handling."""
    assert print_map_action.can_handle_intent("invalid_intent", {"parameters": {"destination": "radiology"}}) is False

def test_can_handle_intent_missing_destination(print_map_action):
    """Test handling of missing destination parameter."""
    assert print_map_action.can_handle_intent("show_map", {"parameters": {}}) is False

def test_execute_show_map_success(print_map_action, mock_gmaps, mock_requests, sample_place_result):
    """Test successful execution of show_map intent."""
    mock_gmaps.places.return_value = sample_place_result
    
    result = print_map_action.execute("show_map", {"parameters": {"destination": "radiology"}})
    
    assert isinstance(result, ActionResult)
    assert result.success is True
    assert "Click the map to view radiology" in result.message
    assert result.data["type"] == "map"
    assert result.data["clickable"] is True
    assert "map_image_path" in result.data["additional_info"]

def test_execute_show_directions_success(print_map_action, mock_gmaps, mock_requests, sample_place_result):
    """Test successful execution of show_directions intent."""
    mock_gmaps.places.return_value = sample_place_result
    
    result = print_map_action.execute("show_directions", {"parameters": {"destination": "emergency"}})
    
    assert isinstance(result, ActionResult)
    assert result.success is True
    assert "Route to emergency" in result.message
    assert result.data["type"] == "map"
    assert result.data["clickable"] is True
    assert "map_image_path" in result.data["additional_info"]

def test_execute_missing_destination(print_map_action):
    """Test execution with missing destination parameter."""
    result = print_map_action.execute("show_map", {"parameters": {}})
    
    assert isinstance(result, ActionResult)
    assert result.success is False
    assert "No destination specified" in result.message

def test_execute_places_api_empty_results(print_map_action, mock_gmaps):
    """Test handling of empty Places API results."""
    mock_gmaps.places.return_value = {'results': []}
    
    result = print_map_action.execute("show_map", {"parameters": {"destination": "nonexistent"}})
    
    assert isinstance(result, ActionResult)
    assert result.success is False
    assert "Could not find" in result.message

def test_execute_map_download_error(print_map_action, mock_gmaps, mock_requests, sample_place_result):
    """Test handling of map download error."""
    mock_gmaps.places.return_value = sample_place_result
    mock_requests.return_value.raise_for_status.side_effect = Exception("Failed to download map")
    
    result = print_map_action.execute("show_map", {"parameters": {"destination": "radiology"}})
    
    assert isinstance(result, ActionResult)
    assert result.success is False
    assert "Failed to download map" in result.message
    assert result.data["type"] == "error"
    assert "error" in result.data

def test_get_ui_data(print_map_action):
    """Test UI data configuration."""
    ui_data = print_map_action.get_ui_data()
    assert ui_data["icon"] == "🗺️"
    assert ui_data["color"] == "#4CAF50"


def test_execute_show_map_invalid_api_key(print_map_action, mock_gmaps):
    """Test map action handling when an invalid API key is used."""
    mock_gmaps.places.side_effect = Exception("Invalid API key")

    result = print_map_action.execute(
        "show_map", {"parameters": {"destination": "radiology"}}
    )

    assert isinstance(result, ActionResult)
    assert result.success is False
    assert "Invalid API key" in result.message
    assert result.data["type"] == "error"
    assert "error" in result.data


def test_execute_show_map_network_error(
    print_map_action, mock_gmaps, mock_requests, sample_place_result
):
    """Test map action handling when a network error occurs during map download."""
    mock_gmaps.places.return_value = sample_place_result
    mock_requests.return_value.raise_for_status.side_effect = Exception("Network Error")

    result = print_map_action.execute(
        "show_map", {"parameters": {"destination": "radiology"}}
    )

    assert isinstance(result, ActionResult)
    assert result.success is False
    assert "Network Error" in result.message
    assert result.data["type"] == "error"
    assert "error" in result.data


def test_execute_show_map_unexpected_response(print_map_action, mock_gmaps):
    """Test map action handling when the Google Maps API returns unexpected results."""
    mock_gmaps.places.return_value = {}

    result = print_map_action.execute(
        "show_map", {"parameters": {"destination": "radiology"}}
    )

    assert isinstance(result, ActionResult)
    assert result.success is False
    assert "Could not find" in result.message
    assert result.data["type"] == "error"


def test_execute_show_map_general_exception(print_map_action, mock_gmaps):
    """Test map action handling when an unexpected exception occurs."""
    mock_gmaps.places.side_effect = Exception("Unexpected error occurred")

    result = print_map_action.execute(
        "show_map", {"parameters": {"destination": "radiology"}}
    )

    assert isinstance(result, ActionResult)
    assert result.success is False
    assert "Unexpected error" in result.message
    assert result.data["type"] == "error"
    assert "error" in result.data
