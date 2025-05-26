import os
import yaml
from services.intent_actions.actions.base import BaseAction, ActionResult
from utils.log_config import logger

DOCUMENTS_YAML = os.path.join(os.path.dirname(__file__), "documents.yaml")

def load_documents_config():
    if not os.path.exists(DOCUMENTS_YAML):
        return {}
    with open(DOCUMENTS_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data.get("documents", {})

class PrintDocumentAction(BaseAction):
    def __init__(self):
        self.documents = load_documents_config()

    @property
    def action_id(self) -> str:
        return "print_document"

    @property
    def display_name(self) -> str:
        return "Print Document"

    @property
    def description(self) -> str:
        return "Prints a PDF document from a configured folder."

    def can_handle_intent(self, intent_name: str, metadata: dict) -> bool:
        logger.info(f"can_handle_intent, {intent_name} {metadata}")
        return intent_name == "print_document"

    def execute(self, intent_name: str, metadata: dict) -> ActionResult:
        # Try to extract the document name from entities
        doc_name = None
        entities = metadata.get("parameters", [])
        for ent in entities:
            print (f"Entity: {ent}")
            if ent.get("entity") == "DOCUMENT":
                doc_name = ent.get("value")
                break

        if not doc_name:
            print("No document name found in metadata.")
            return ActionResult(
                success=True,
                message="Hello, World!",
                data={"type": "info", "content": "Hello, World!"}
            )

        # Try to find the document (case-insensitive match)
        matched_doc = next((k for k in self.documents if k.lower() == doc_name.lower()), None)
        if not matched_doc:
            return ActionResult(
                success=False,
                message=f"Document '{doc_name}' not found in configuration.",
                data={"type": "error"}
            )

        file_path = self.documents[matched_doc]
        if not os.path.exists(file_path):
            return ActionResult(
                success=False,
                message=f"File for '{matched_doc}' not found at {file_path}.",
                data={"type": "error"}
            )


        # Here you would add your actual print logic
        # For now, just simulate success
        return ActionResult(
            success=True,
            message=f"Printing document: {matched_doc}",
            data={"type": "info", "file": file_path}
        )

    def get_ui_data(self) -> dict:
        return {
            "icon": "🖨️",
            "color": "#4CAF50"
        }

exported_actions = [PrintDocumentAction]