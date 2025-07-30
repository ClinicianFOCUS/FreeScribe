"""
Intent patterns for showing maps and finding locations.
"""

from services.intent_actions.intents.spacy_recognizer import SpacyIntentPattern, SpacyEntityPattern

exported_patterns = [
    SpacyIntentPattern(
        intent_name="show_map",
        patterns=[
            [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "a"}, {"LOWER": "map"}],
            [{"LOWER": "show"}, {"LOWER": "map"}],
            [{"LOWER": "display"}, {"LOWER": "map"}],
            [{"LOWER": "map"}, {"LOWER": "of"}],
            [{"LOWER": "view"}, {"LOWER": "map"}],
            [{"LOWER": "print"}, {"LOWER": "map"}],
            [{"LOWER": "show"}, {"LOWER": "me"}, {"LOWER": "map"}, {"LOWER": "of"}],
        ],
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    ),
    SpacyIntentPattern(
        intent_name="find_location",
        patterns=[
            [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "cafeteria"}],
            [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "entrance"}],
            [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "wing"}],
            [{"LOWER": "where"}, {"LOWER": "is"}, {"LOWER": "the"}, {"LEMMA": "department"}],
            [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "cafeteria"}],
            [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "entrance"}],
            [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "wing"}],
            [{"LOWER": "need"}, {"LOWER": "to"}, {"LOWER": "find"}, {"LOWER": "the"}, {"LEMMA": "department"}],
            [{"LOWER": "locate"}, {"LOWER": "the"}],
            [{"LOWER": "find"}, {"LOWER": "location"}, {"LOWER": "of"}],
        ],
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    )
]

exported_entities = [
    # Medical facility entities
    SpacyEntityPattern(
        entity_name="MEDICAL_FACILITY",
        patterns=[
            [{"LOWER": "radiology"}],
            [{"LOWER": "emergency"}],
            [{"LOWER": "emergency"}, {"LOWER": "room"}],
            [{"LOWER": "er"}],
            [{"LOWER": "intensive"}, {"LOWER": "care"}],
            [{"LOWER": "icu"}],
            [{"LOWER": "surgery"}],
            [{"LOWER": "operating"}, {"LOWER": "room"}],
            [{"LOWER": "or"}],
            [{"LOWER": "maternity"}],
            [{"LOWER": "pediatrics"}],
            [{"LOWER": "oncology"}],
            [{"LOWER": "cardiology"}],
            [{"LOWER": "neurology"}],
            [{"LOWER": "orthopedics"}],
        ]
    ),
    # Building areas
    SpacyEntityPattern(
        entity_name="BUILDING_AREA",
        patterns=[
            [{"LOWER": "north"}, {"LOWER": "wing"}],
            [{"LOWER": "south"}, {"LOWER": "wing"}],
            [{"LOWER": "east"}, {"LOWER": "wing"}],
            [{"LOWER": "west"}, {"LOWER": "wing"}],
            [{"LOWER": "main"}, {"LOWER": "entrance"}],
            [{"LOWER": "lobby"}],
            [{"LOWER": "reception"}],
            [{"LOWER": "information"}, {"LOWER": "desk"}],
        ]
    )
]