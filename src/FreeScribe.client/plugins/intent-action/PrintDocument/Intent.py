import os
import yaml
from services.intent_actions.intents.spacy_recognizer import SpacyIntentPattern, SpacyEntityPattern

DOCUMENTS_YAML = os.path.join(os.path.dirname(__file__), "documents.yaml")

def load_documents_config():
    """Load document configurations from YAML file."""
    if not os.path.exists(DOCUMENTS_YAML):
        return {}
    
    with open(DOCUMENTS_YAML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def generate_entity_patterns():
    """Generate SpacyEntityPattern objects from the documents configuration."""
    config = load_documents_config()
    all_patterns = []
    
    # Collect all patterns from all documents
    for doc_entry in config.get("documents", []):
        for doc_name, doc_details in doc_entry.items():
            doc_info = doc_details[0] if doc_details else {}
            patterns = doc_info.get("patterns", [])
            if patterns:
                all_patterns.extend(patterns)
    
    # Create a single entity pattern with all document patterns
    return [
        SpacyEntityPattern(
            entity_name="DOCUMENT",
            patterns=all_patterns
        )
    ]

def generate_document_map():
    """Generate document mapping from the documents configuration."""
    config = load_documents_config()
    document_map = {}
    
    # Create mapping from document_id to file_path
    for doc_entry in config.get("documents", []):
        for doc_name, doc_details in doc_entry.items():
            doc_info = doc_details[0] if doc_details else {}
            doc_id = doc_info.get("document_id", "")
            file_path = doc_info.get("file_path", "")
            if doc_id and file_path:
                document_map[doc_id] = file_path
    
    return document_map

# Generated entity patterns and document map
exported_entities = generate_entity_patterns()
entity_to_document_map = generate_document_map()

# Intent patterns
exported_patterns = [
    SpacyIntentPattern(
        intent_name="print_document",
        patterns=[
            # Generic patterns with a document entity
            [{"LOWER": "print"}, {"ENT_TYPE": "DOCUMENT"}],
            [{"LOWER": "print"}, {"LOWER": "the"}, {"ENT_TYPE": "DOCUMENT"}],
            [{"LOWER": "print"}, {"LOWER": "a"}, {"ENT_TYPE": "DOCUMENT"}],
            [{"LOWER": "give"}, {"LOWER": "you"}, {"ENT_TYPE": "DOCUMENT"}],
            [{"LOWER": "give"}, {"LOWER": "you"}, {"LOWER": "the"}, {"ENT_TYPE": "DOCUMENT"}],
            [{"LOWER": "give"}, {"LOWER": "you"}, {"LOWER": "a"}, {"ENT_TYPE": "DOCUMENT"}],
            [{"LOWER": "print"}, {"ENT_TYPE": "DOCUMENT"}, {"LOWER": "file"}],
            [{"LOWER": "print"}, {"LOWER": "file"}, {"ENT_TYPE": "DOCUMENT"}],
            [{"LOWER": "give"}, {"ENT_TYPE": "DOCUMENT"}],
        ],
        required_entities=[],  # Require a document entity for matching
    )
]