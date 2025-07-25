"""
This is an example of a simple intent action plugin that recognizes the phrase "hello world".
"""

from services.intent_actions.intents.spacy_recognizer import SpacyIntentPattern, SpacyEntityPattern

exported_patterns = [
    SpacyIntentPattern(
        intent_name="hello_world",
        patterns=[
            [{"LOWER": "hello"}, {"LOWER": "world"}],
            [{"LOWER": "hello"}, {"ENT_TYPE": "GREETING_TARGET"}],  # Pattern using custom entity
            [{"LOWER": "greet"}, {"ENT_TYPE": "GREETING_TARGET"}],
        ],
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    ),
    SpacyIntentPattern(
        intent_name="greet",
        patterns=[
            [{"LOWER": "greet"}, {"ENT_TYPE": "GREETING_TARGET"}],
            [ {"LOWER": "hello"}, {"ENT_TYPE": "GREETING_TARGET"}],
        ],
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    )
]

exported_entities = [
    SpacyEntityPattern(
        entity_name="GREETING_TARGET",
        patterns=[
            [{"LOWER": "world"}],
            [{"LOWER": "universe"}],
            [{"LOWER": "everyone"}],
            [{"LOWER": "there"}],
            [{"LOWER": "friend"}],
            [{"LOWER": "buddy"}],
        ]
    )
]