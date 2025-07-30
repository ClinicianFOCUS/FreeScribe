"""
Intent patterns for showing maps and finding locations.
"""

from services.intent_actions.intents.spacy_recognizer import SpacyIntentPattern, SpacyEntityPattern

# Map-related phrases
map_phrases = [
    "show me a map",
    "show map", 
    "display map",
    "map of",
    "view map",
    "print map",
    "show me map of"
]

# Generate map patterns from phrases
map_patterns = [
    [{"LOWER": tok} for tok in phrase.split()]
    for phrase in map_phrases
]

# Find location templates and entities
locate_templates = [
    (["where", "is", "the"], True),
    (["need", "to", "find", "the"], True),
    (["locate", "the"], False),
    (["find", "location", "of"], False),
]

location_entities = ["cafeteria", "entrance", "wing", "department"]

# Generate location patterns
location_patterns = []
for tokens, needs_entity in locate_templates:
    token_pattern = [{"LOWER": tok} for tok in tokens]
    if needs_entity:
        location_patterns += [
            token_pattern + [{"LEMMA": ent}]
            for ent in location_entities
        ]
    else:
        location_patterns.append(token_pattern)

exported_patterns = [
    SpacyIntentPattern(
        intent_name="show_map",
        patterns=map_patterns,
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    ),
    SpacyIntentPattern(
        intent_name="find_location",
        patterns=location_patterns,
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    )
]

# Medical facility names
medical_facilities = [
    "radiology",
    "emergency", 
    "emergency room",
    "er",
    "intensive care",
    "icu",
    "surgery",
    "operating room",
    "or",
    "maternity",
    "pediatrics",
    "oncology",
    "cardiology",
    "neurology",
    "orthopedics"
]

# Building area names
building_areas = [
    "north wing",
    "south wing", 
    "east wing",
    "west wing",
    "main entrance",
    "lobby",
    "reception",
    "information desk"
]

exported_entities = [
    SpacyEntityPattern(
        entity_name="MEDICAL_FACILITY",
        patterns=[
            [{"LOWER": token} for token in facility.split()]
            for facility in medical_facilities
        ]
    ),
    SpacyEntityPattern(
        entity_name="BUILDING_AREA",
        patterns=[
            [{"LOWER": token} for token in area.split()]
            for area in building_areas
        ]
    )
]