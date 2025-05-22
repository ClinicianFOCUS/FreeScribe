"""
Unit tests for the base action class.
"""

import pytest
from typing import Dict, Any
from services.intent_actions.actions.base import BaseAction, ActionResult

class TestAction(BaseAction):
    """Test implementation of BaseAction."""
    
    @property
    def action_id(self) -> str:
        return "test_action"
    
    @property
    def display_name(self) -> str:
        return "Test Action"
    
    @property
    def description(self) -> str:
        return "Test action description"
    
    def can_handle_intent(self, intent_name: str, metadata: Dict[str, Any]) -> bool:
        return intent_name == "test_intent"
    
    def execute(self, intent_name: str, metadata: Dict[str, Any]) -> ActionResult:
        return ActionResult(
            success=True,
            message="Test execution successful",
            data={"test": "data"}
        )
    
    def get_ui_data(self) -> Dict[str, Any]:
        return {"icon": "🔍", "color": "#000000"}

@pytest.fixture
def test_action():
    """Create a test action instance."""
    return TestAction()

def test_action_properties(test_action):
    """Test that action properties return correct values."""
    assert test_action.action_id == "test_action"
    assert test_action.display_name == "Test Action"
    assert test_action.description == "Test action description"

def test_can_handle_intent(test_action):
    """Test intent handling capability."""
    assert test_action.can_handle_intent("test_intent", {}) is True
    assert test_action.can_handle_intent("other_intent", {}) is False

def test_execute(test_action):
    """Test action execution."""
    result = test_action.execute("test_intent", {})
    assert isinstance(result, ActionResult)
    assert result.success is True
    assert result.message == "Test execution successful"
    assert result.data == {"test": "data"}

def test_get_ui_data(test_action):
    """Test UI data retrieval."""
    ui_data = test_action.get_ui_data()
    assert ui_data == {"icon": "🔍", "color": "#000000"}

def test_action_result_creation():
    """Test ActionResult creation with different parameters."""
    # Test with all parameters
    result1 = ActionResult(
        success=True,
        message="Test message",
        data={"key": "value"}
    )
    assert result1.success is True
    assert result1.message == "Test message"
    assert result1.data == {"key": "value"}
    
    # Test without optional data
    result2 = ActionResult(
        success=False,
        message="Error message"
    )
    assert result2.success is False
    assert result2.message == "Error message"
    assert result2.data is None 