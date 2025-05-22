from services.intent_actions.actions.base import BaseAction, ActionResult

class HelloWorldAction(BaseAction):
    @property
    def action_id(self) -> str:
        return "hello_world"

    @property
    def display_name(self) -> str:
        return "Hello World"

    @property
    def description(self) -> str:
        return "Responds with a friendly Hello World message."

    def can_handle_intent(self, intent_name: str, metadata: dict) -> bool:
        return intent_name == "hello_world"

    def execute(self, intent_name: str, metadata: dict) -> ActionResult:
        return ActionResult(
            success=True,
            message="Hello, World!",
            data={"type": "info", "content": "Hello, World!"}
        )

    def get_ui_data(self) -> dict:
        return {
            "icon": "👋",
            "color": "#2196F3"
        }

# Export the action for plugin loader
exported_actions = [HelloWorldAction]