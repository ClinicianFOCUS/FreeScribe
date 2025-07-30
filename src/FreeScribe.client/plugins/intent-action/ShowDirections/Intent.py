"""
Intent patterns for showing directions using Google Maps.
"""

from services.intent_actions.intents.spacy_recognizer import SpacyIntentPattern, SpacyEntityPattern

exported_patterns = [
    SpacyIntentPattern(
        intent_name="show_directions",
        patterns=[
            [{"LOWER": "go"}, {"LOWER": "to"}],
            [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}],
            [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "go"}, {"LOWER": "to"}],
            [{"LOWER": "directions"}, {"LOWER": "to"}],
            [{"LOWER": "how"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}],
            [{"LOWER": "where"}, {"LOWER": "is"}],
            [{"LOWER": "find"}],
            [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "to"}],
            # Hospital-specific patterns
            [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}, {"ENT_TYPE": "ORG"}],
            [{"LOWER": "where"}, {"LOWER": "is"}, {"ENT_TYPE": "ORG"}],
            [{"LOWER": "need"}, {"LOWER": "directions"}, {"LOWER": "to"}, {"ENT_TYPE": "ORG"}],
            [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "how"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}, {"ENT_TYPE": "ORG"}],
            [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LOWER": "main"}, {"LOWER": "entrance"}],
            [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}, {"ENT_TYPE": "ORG"}],
            [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "the"}, {"LOWER": "way"}, {"LOWER": "to"}],
            # Emergency room specific patterns
            [{"LOWER": "get"}, {"LOWER": "to"}, {"LOWER": "emergency"}, {"LOWER": "room"}],
            [{"LOWER": "find"}, {"LOWER": "emergency"}, {"LOWER": "room"}],
            # Cardiac care specific patterns
            [{"LOWER": "find"}, {"LEMMA": "cardiac"}, {"LEMMA": "care"}],
            [{"LOWER": "get"}, {"LOWER": "to"}, {"LEMMA": "cardiac"}, {"LEMMA": "care"}],
            # Cafeteria specific patterns
            [{"LOWER": "way"}, {"LOWER": "to"}, {"LOWER": "cafeteria"}],
            [{"LOWER": "find"}, {"LOWER": "cafeteria"}],
            [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "cafeteria"}],
            # General patterns
            [{"LOWER": "need"}, {"LOWER": "directions"}, {"LOWER": "to"}],
            [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "how"}, {"LOWER": "to"}, {"LOWER": "get"}, {"LOWER": "to"}],
            [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}],
            [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}],
            [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "the"}, {"LOWER": "way"}, {"LOWER": "to"}],
            # Department-specific patterns
            [{"LOWER": "get"}, {"LOWER": "to"}, {"LOWER": "the"}, {"LEMMA": "department"}],
            [{"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "department"}],
            [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "department"}],
            # Wing/entrance patterns
            [{"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "wing"}],
            [{"LOWER": "get"}, {"LOWER": "to"}, {"LOWER": "the"}, {"LEMMA": "wing"}],
            [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "entrance"}],
            [{"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "entrance"}],
        ],
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    )
]

exported_entities = [
    # Add location-related entities
    SpacyEntityPattern(
        entity_name="LOCATION",
        patterns=[
            [{"LOWER": "emergency"}, {"LOWER": "room"}],
            [{"LOWER": "cafeteria"}],
            [{"LOWER": "cardiac"}, {"LOWER": "care"}],
            [{"LOWER": "main"}, {"LOWER": "entrance"}],
            [{"LOWER": "parking"}, {"LOWER": "garage"}],
            [{"LOWER": "elevator"}],
            [{"LOWER": "stairs"}],
            [{"LOWER": "restroom"}],
            [{"LOWER": "bathroom"}],
            [{"LOWER": "gift"}, {"LOWER": "shop"}],
        ]
    )
]