from services.intent_actions.intents.spacy_recognizer import SpacyIntentPattern

exported_patterns = [
    SpacyIntentPattern(
        intent_name="hello_world",
        patterns=[
            [{"LOWER": "hello"}, {"LOWER": "world"}],
        ],
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    )
]