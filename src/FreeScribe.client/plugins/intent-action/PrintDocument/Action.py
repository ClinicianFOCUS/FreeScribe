import os
import yaml
from services.intent_actions.actions.base import BaseAction, ActionResult
from utils.log_config import logger

DOCUMENTS_YAML = os.path.join(os.path.dirname(__file__), "documents.yaml")

import os
import yaml
from services.intent_actions.actions.base import BaseAction, ActionResult
from utils.log_config import logger

DOCUMENTS_YAML = os.path.join(os.path.dirname(__file__), "documents.yaml")

def load_documents_config():
    """Load document file paths from the YAML configuration."""
    if not os.path.exists(DOCUMENTS_YAML):
        return {}
        
    with open(DOCUMENTS_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        documents = {}
        
        for doc_entry in data.get("documents", []):
            for doc_name, doc_details in doc_entry.items():
                # Extract document details from the first item in doc_details
                doc_info = doc_details[0] if doc_details else {}
                doc_id = doc_info.get("document_name", "")
                file_path = doc_info.get("file_path", "")
                if doc_id and file_path:
                    documents[doc_id] = file_path
                    
        return documents

class PrintDocumentAction(BaseAction):
    def __init__(self):
        self.documents = load_documents_config()
        logger.info(f"Loaded documents configuration: {self.documents}")

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
            if ent == "document_type":
                doc_name = entities[ent]
                break

        if not doc_name:
            print("No document name found in metadata.")
            return ActionResult(
                success=True,
                message="Hello, World!",
                data={"type": "info", "content": "Hello, World!"}
            )

        # # Try to find the document (case-insensitive match)
        logger.info(f"reconized documents: {self.documents}")
        matched_doc = next((k for k in self.documents if k.lower() == doc_name.lower()), None)
        logger.info(f"Matched document: {matched_doc}")


        # Here you would add your actual print logic
        # For now, just simulate success
        #send to system print dialog
        import subprocess
        import platform
        
        file_ext = os.path.splitext(self.documents[matched_doc])[1].lower()
        
        if platform.system() == "Windows":
            if file_ext in ['.webp', '.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                # For images, try to convert then open
                import tempfile
                from PIL import Image
                
                # Create a temporary PDF file
                temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_pdf.close()
                
                # Convert image to PDF
                img = Image.open(self.documents[matched_doc])
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(temp_pdf.name, 'PDF', resolution=100.0)
                
                # Just open the PDF file instead of trying to print directly
                os.startfile(temp_pdf.name)
            else:
                # For other files, just open them
                os.startfile(self.documents[matched_doc])

        return ActionResult(
            success=True,
            message=f"Printing document {doc_name} guide",
            data={"type": "info"}
        )

    def get_ui_data(self) -> dict:
        return {
            "icon": "🖨️",
            "color": "#4CAF50"
        }

exported_actions = [PrintDocumentAction]