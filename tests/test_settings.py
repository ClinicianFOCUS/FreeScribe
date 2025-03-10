import os
import json
import pytest
import tempfile
import shutil
from typing import List, Dict, Any, Union, Optional
from unittest.mock import patch, MagicMock

# Import the SettingsWindow class with the correct paths
from UI.SettingsWindow import SettingsWindow
from UI.SettingsConstant import SettingsKeys


# Helper function to write a settings file with a dictionary
def write_settings_dict(test_dir: str, content: Dict[str, Any], filename: str = 'settings.txt') -> str:
    """
    Write a dictionary to a settings file in the test directory.
    
    :param test_dir: The test directory
    :param content: The dictionary content to write
    :param filename: The filename to use, defaults to 'settings.txt'
    :return: The path to the created file
    """
    path = os.path.join(test_dir, filename)
    with open(path, 'w') as f:
        json.dump(content, f)
    return path


# Helper function to write a settings file with a string
def write_settings_string(test_dir: str, content: str, filename: str = 'settings.txt') -> str:
    """
    Write a string to a settings file in the test directory.
    
    :param test_dir: The test directory
    :param content: The string content to write
    :param filename: The filename to use, defaults to 'settings.txt'
    :return: The path to the created file
    """
    path = os.path.join(test_dir, filename)
    with open(path, 'w') as f:
        f.write(content)
    return path


# Helper function to verify settings remain unchanged
def verify_settings_unchanged(original_settings: Dict[str, Any], current_settings: Dict[str, Any]) -> None:
    """
    Verify that settings remain unchanged.
    
    :param original_settings: The original settings dictionary
    :param current_settings: The current settings dictionary
    """
    for key, value in original_settings.items():
        assert current_settings[key] == value, \
            f"Setting {key} was changed unexpectedly"


@pytest.fixture
def test_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)


@pytest.fixture
def settings(test_dir):
    """Create a settings instance with mocked resource path."""
    # Patch the get_resource_path function to use our test directory
    with patch('UI.SettingsWindow.get_resource_path') as mock_get_resource_path:
        mock_get_resource_path.side_effect = lambda path: os.path.join(test_dir, path)
        
        # Create a settings instance
        settings_instance = SettingsWindow()
        
        # Mock the main_window attribute
        settings_instance.main_window = None
        
        yield settings_instance


@pytest.fixture
def boolean_setting():
    """Get a specific boolean setting for testing."""
    # Use a known boolean setting from DEFAULT_SETTINGS_TABLE
    return "use_story"  # This is a known boolean setting


@pytest.fixture
def integer_setting():
    """Get a specific integer setting for testing."""
    # Use a known integer setting from DEFAULT_SETTINGS_TABLE
    return "max_context_length"  # This is a known integer setting


@pytest.fixture
def settings_file_path(test_dir):
    """Get the path to the settings file."""
    return os.path.join(test_dir, 'settings.txt')


def test_boolean_settings_save_load(settings, test_dir, boolean_setting, settings_file_path):
    """Test that boolean settings are saved and loaded correctly."""
    # Set the value to True
    settings.editable_settings[boolean_setting] = True
    
    # Save settings
    settings.save_settings_to_file()
    
    # Verify the settings file exists
    assert os.path.exists(settings_file_path), "Settings file was not created"
    
    # Read the file directly to verify the value was saved as a boolean
    with open(settings_file_path, 'r') as f:
        saved_settings = json.load(f)
    
    # Check that the value is saved as a boolean (true), not as a string or integer
    assert isinstance(saved_settings['editable_settings'][boolean_setting], bool), \
        f"Setting {boolean_setting} was not saved as a boolean"
    assert saved_settings['editable_settings'][boolean_setting] is True, \
        f"Setting {boolean_setting} value was not saved correctly"
    
    # Change the value in memory
    settings.editable_settings[boolean_setting] = False
    
    # Load settings
    settings.load_settings_from_file()
    
    # Verify the value was loaded correctly as a boolean
    assert isinstance(settings.editable_settings[boolean_setting], bool), \
        f"Setting {boolean_setting} was not loaded as a boolean"
    assert settings.editable_settings[boolean_setting] is True, \
        f"Setting {boolean_setting} value was not loaded correctly"


def test_integer_settings_save_load(settings, test_dir, integer_setting, settings_file_path):
    """Test that integer settings are saved and loaded correctly."""
    # Set the value to a test integer
    test_value = 42
    settings.editable_settings[integer_setting] = test_value
    
    # Save settings
    settings.save_settings_to_file()
    
    # Verify the settings file exists
    assert os.path.exists(settings_file_path), "Settings file was not created"
    
    # Read the file directly to verify the value was saved as an integer
    with open(settings_file_path, 'r') as f:
        saved_settings = json.load(f)
    
    # Check that the value is saved as an integer, not as a string
    assert isinstance(saved_settings['editable_settings'][integer_setting], int), \
        f"Setting {integer_setting} was not saved as an integer"
    assert saved_settings['editable_settings'][integer_setting] == test_value, \
        f"Setting {integer_setting} value was not saved correctly"
    
    # Change the value in memory
    settings.editable_settings[integer_setting] = 0
    
    # Load settings
    settings.load_settings_from_file()
    
    # Verify the value was loaded correctly as an integer
    assert isinstance(settings.editable_settings[integer_setting], int), \
        f"Setting {integer_setting} was not loaded as an integer"
    assert settings.editable_settings[integer_setting] == test_value, \
        f"Setting {integer_setting} value was not loaded correctly"


def test_mixed_settings_save_load(settings, test_dir, boolean_setting, integer_setting):
    """Test that a mix of boolean and integer settings are saved and loaded correctly."""
    # Set test values
    bool_value = True
    int_value = 42
    settings.editable_settings[boolean_setting] = bool_value
    settings.editable_settings[integer_setting] = int_value
    
    # Save settings
    settings.save_settings_to_file()
    
    # Change the values in memory
    settings.editable_settings[boolean_setting] = False
    settings.editable_settings[integer_setting] = 0
    
    # Load settings
    settings.load_settings_from_file()
    
    # Verify both values were loaded correctly with the right types
    assert isinstance(settings.editable_settings[boolean_setting], bool), \
        f"Setting {boolean_setting} was not loaded as a boolean"
    assert settings.editable_settings[boolean_setting] == bool_value, \
        f"Setting {boolean_setting} value was not loaded correctly"
    
    assert isinstance(settings.editable_settings[integer_setting], int), \
        f"Setting {integer_setting} was not loaded as an integer"
    assert settings.editable_settings[integer_setting] == int_value, \
        f"Setting {integer_setting} value was not loaded correctly"


def test_integer_to_boolean_conversion(settings, test_dir, boolean_setting, settings_file_path):
    """Test that integer representations of booleans (0/1) are converted correctly."""
    # Create a settings file with an integer representation of a boolean
    settings_data = {
        "openai_api_key": "test_key",
        "editable_settings": {
            boolean_setting: 1  # Integer representation of True
        },
        "app_version": "1.0.0"
    }
    
    # Write the settings file
    write_settings_dict(test_dir, settings_data)
    
    # Load settings
    settings.load_settings_from_file()
    
    # Verify the value was converted to a boolean
    assert isinstance(settings.editable_settings[boolean_setting], bool), \
        f"Setting {boolean_setting} was not converted to a boolean"
    assert settings.editable_settings[boolean_setting] is True, \
        f"Setting {boolean_setting} value was not converted correctly"


def test_string_to_integer_conversion(settings, test_dir, integer_setting, settings_file_path):
    """Test that string representations of integers are converted correctly."""
    # Create a settings file with a string representation of an integer
    settings_data = {
        "openai_api_key": "test_key",
        "editable_settings": {
            integer_setting: "42"  # String representation of integer
        },
        "app_version": "1.0.0"
    }
    
    # Write the settings file
    write_settings_dict(test_dir, settings_data)
    
    # Load settings
    settings.load_settings_from_file()
    
    # Verify the value was converted to an integer
    assert isinstance(settings.editable_settings[integer_setting], int), \
        f"Setting {integer_setting} was not converted to an integer"
    assert settings.editable_settings[integer_setting] == 42, \
        f"Setting {integer_setting} value was not converted correctly"


def test_invalid_string_to_integer_conversion(settings, integer_setting):
    """Test that an invalid string for integer conversion is handled gracefully."""
    # Backup the original value so that tests remain isolated
    original_value = settings.editable_settings.get(integer_setting, None)
    
    # Set an invalid string value that cannot be converted to an integer
    invalid_value = "invalid_int"
    settings.editable_settings[integer_setting] = invalid_value
    
    # Call the convert_setting_value method directly
    result = settings.convert_setting_value(
        integer_setting, invalid_value
    )
    
    # The method should return the original value when conversion fails
    assert result == invalid_value, \
        "Invalid string should be returned as-is when conversion to integer fails"
    
    # The method should not modify the original value in editable_settings
    assert settings.editable_settings[integer_setting] == invalid_value, \
        "Original invalid value in editable_settings should not be modified"
    
    # Always restore the original value after the test
    # Use a default value (e.g., 0) if original_value was None
    settings.editable_settings[integer_setting] = original_value if original_value is not None else 0


def test_invalid_json_settings(settings, test_dir, settings_file_path):
    """Test how settings handle an invalid JSON file."""
    # Create an invalid JSON content
    invalid_json = "{invalid: 'json', missing quotes}"  # intentionally invalid JSON
    
    # Write the invalid JSON to the settings file
    write_settings_string(test_dir, invalid_json)
    
    # Save the original settings to compare later
    original_settings = settings.editable_settings.copy()
    
    # Load settings - should not raise an exception
    settings.load_settings_from_file()
    
    # Verify that the settings remain unchanged when loading invalid JSON
    verify_settings_unchanged(original_settings, settings.editable_settings)


def test_settings_missing_keys(settings, test_dir, settings_file_path):
    """Test how settings behave when required keys are missing."""
    # Create a settings file missing required keys
    incomplete_settings = '{"openai_api_key": "test_key"}'  # Missing editable_settings
    
    # Write the incomplete settings to the settings file
    write_settings_string(test_dir, incomplete_settings)
    
    # Save the original settings to compare later
    original_settings = settings.editable_settings.copy()
    
    # Load settings - should not raise an exception
    settings.load_settings_from_file()
    
    # Verify that the settings remain unchanged when loading incomplete settings
    verify_settings_unchanged(original_settings, settings.editable_settings)


def test_settings_extra_data(settings, test_dir, boolean_setting, settings_file_path):
    """Test how settings behave when the settings file contains extra unexpected data."""
    # Create a settings file with extra keys not defined in the schema
    extra_data_settings = {
        "openai_api_key": "test_key",
        "editable_settings": {
            boolean_setting: True,
            "unexpectedKey": "unexpectedValue"
        },
        "app_version": "1.0.0",
        "extraTopLevelKey": "extraTopLevelValue"
    }
    
    # Write the settings with extra data to the settings file
    write_settings_dict(test_dir, extra_data_settings)
    
    # Load settings - should not raise an exception
    settings.load_settings_from_file()
    
    # Verify that the known setting was loaded correctly
    assert settings.editable_settings[boolean_setting] is True, \
        f"Known setting {boolean_setting} was not loaded correctly"
    
    # Verify that the unexpected key was not added to editable_settings
    assert "unexpectedKey" not in settings.editable_settings, \
        "Unexpected key was added to editable_settings" 