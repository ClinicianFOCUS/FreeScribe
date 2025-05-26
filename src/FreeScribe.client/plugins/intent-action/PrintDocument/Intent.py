from services.intent_actions.intents.spacy_recognizer import SpacyIntentPattern, SpacyEntityPattern

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

# Define custom entities for this plugin
exported_entities = [
    SpacyEntityPattern(
        entity_name="DOCUMENT",
        patterns=[
            # patern for blood pressure handout
            [{"LOWER": "blood"}, {"LOWER": "pressure"}],
        ]
    ),
    SpacyEntityPattern(
        entity_name="RANDOM_DOCUMENT",
        patterns=[
            # patern for blood sugar handout
            [{"LOWER": "blood"}, {"LOWER": "sugar"}],
        ]
    ),
]

entity_to_document_map = {
    "blood_pressure": "BloodPressureHandout.pdf",
    "blood_sugar": "BloodSugarHandout.pdf",
}