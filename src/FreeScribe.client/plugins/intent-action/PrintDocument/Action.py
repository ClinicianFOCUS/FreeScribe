import os
import yaml
import tempfile
from PIL import Image
from services.intent_actions.actions.base import BaseAction, ActionResult
from utils.log_config import logger
from utils.file_utils import get_resource_path

DOCUMENTS_YAML = os.path.join(os.path.dirname(__file__), "documents.yaml")
DOCUMENTS_PATH = get_resource_path("plugins/intent-action/PrintDocument/documents")

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
                # if is absoulte path use it if not get resource path
                if not os.path.isabs(file_path):
                    file_path = DOCUMENTS_PATH + os.sep + file_path
                    logger.debug(f"Using relative path for {doc_id}: {file_path}")
                else:
                    file_path = file_path.strip()

                doc_info["file_path"] = file_path

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
        entities = metadata.get("parameters", {})
        if "document_type" in entities:
            doc_name = entities["document_type"]

        if not doc_name:
            print("No document name found in metadata.")
            return ActionResult(
                success=False,
                message="No document name found in metadata.",
                data={"type": "error", "content": "No document name could be extracted from the provided metadata."}
            )

        # # Try to find the document (case-insensitive match)
        logger.info(f"reconized documents: {self.documents}")
        matched_doc = next((k for k in self.documents if k.lower() == doc_name.lower()), None)
        logger.info(f"Matched document: {matched_doc}")

        if not matched_doc:
            return ActionResult(
                success=False,
                message=f"Document '{doc_name}' not found in configuration.",
                data={"type": "error", "content": f"No document matching '{doc_name}' was found in the configured documents."}
            )

        if not self.documents[matched_doc]:
            return ActionResult(
                success=False,
                message=f"Document '{matched_doc}' has no file path configured.",
                data={"type": "error", "content": f"The document '{matched_doc}' does not have a valid file path configured."}
            )

        data={
            "type": "info",
            "document_name": doc_name,
            "matched_doc": matched_doc,
            "file_path": self.documents[matched_doc],
            "has_action": True,
            "auto_complete": False,
        }

        data["action"] = lambda: self.complete_action(data)

        # Return success with document info for completion
        return ActionResult(
            success=True,
            message=f"Ready to print document {doc_name}",
            data=data
        )

    def complete_action(self, result_data: dict) -> bool:
        """
        Complete the action by opening/printing the document.
        
        :param result_data: Data returned from the action execution
        :return: True if the action was successfully completed
        """
        try:
            file_path = result_data.get("file_path")
            if not file_path:
                logger.error("No file path provided in result data")
                return False
            
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in ['.webp', '.jpg', '.jpeg', '.png', '.gif', '.bmp']:              
                # Create a temporary PDF file
                temp_pdf = tempfile.NamedTemporaryFile(delete=True, suffix='.pdf')
                temp_pdf.close()
                
                # Convert image to PDF
                img = Image.open(file_path)
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(temp_pdf.name, 'PDF', resolution=100.0)
                
                # Just open the PDF file instead of trying to print directly
                os.startfile(temp_pdf.name)
             
                logger.info(f"Successfully opened document: {file_path}")
                return True
            else:
                logger.warning(f"Unsupported file type: {file_ext}. Only image files are supported for printing.")
                return False
            
        except Exception as e:
            logger.error(f"Error completing print document action: {e}")
            return False

    def get_ui_data(self) -> dict:
        return {
            "icon": "🖨️",
            "color": "#4CAF50"
        }

exported_actions = [PrintDocumentAction]