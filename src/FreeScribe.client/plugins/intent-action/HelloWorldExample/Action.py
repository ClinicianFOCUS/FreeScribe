from services.intent_actions.actions.base import BaseAction, ActionResult
from utils.log_config import logger

class HelloWorldAction(BaseAction):
    """
    HelloWorldAction is a simple action that responds with a friendly Hello World message.
    
    It is designed to demonstrate the structure and functionality of an action plugin.
    """
    @property
    def action_id(self) -> str:
        """
        Unique identifier for the action. This should be a string that is unique across all actions."""
        return "hello_world"

    @property
    def display_name(self) -> str:
        """
        Display name for the action. This is the name that will be shown in the UI.
        """
        return "Hello World"

    @property
    def description(self) -> str:
        """
        Description of the action. This should provide a brief overview of what the action does.
        """
        return "Responds with a friendly Hello World message."

    def can_handle_intent(self, intent_name: str, metadata: dict) -> bool:
        """
        Check if the action can handle the given intent.

        :param intent_name: The name of the intent to check.
        :param metadata: Additional metadata related to the intent.
        :return: True if the action can handle the intent, False otherwise.
        """
        return intent_name == "hello_world"

    def execute(self, intent_name: str, metadata: dict) -> ActionResult:
        """
        Execute the action for the given intent.
        
        :param intent_name: The name of the intent to execute.
        :param metadata: Additional metadata related to the intent.
        :return: An ActionResult object containing the result of the action execution.
        """
        data= {
            "type": "info",
            "content": "Hello, World!",
            "auto_complete": True,
            "has_action": True
        }

        data["action"] = lambda: self.complete_action(data)

        return ActionResult(
            success=True,
            message="Hello, World!",
            data=data
        )

    def complete_action(self, result_data):
        """
        Complete the action after execution.
        
        :param result_data: Data returned from the action execution.
        :return: True if the action was completed successfully, False otherwise.
        """
        # Here we could implement any finalization logic if needed
        logger.info("HelloWorldAction completed successfully.")
        return True


    def get_ui_data(self) -> dict:
        """
        Get UI data for the action. This can include icons, colors, and other UI-related information.
        """
        return {
            "icon": "👋",
            "color": "#2196F3"
        }

# Export the action for plugin loader
exported_actions = [HelloWorldAction]