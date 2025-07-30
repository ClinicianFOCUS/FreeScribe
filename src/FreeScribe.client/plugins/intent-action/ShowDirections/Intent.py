"""
Intent patterns for showing directions using Google Maps.
"""

from services.intent_actions.intents.spacy_recognizer import SpacyIntentPattern, SpacyEntityPattern

# Define phrase groups for generating direction patterns
PHRASE_GROUPS = {
    "base": [
        "go to",
        "need to get to", 
        "need to go to",
        "directions to",
        "how to get to",
        "where is",
        "find",
        "show me to",
        "show me how to get to",
        "show me the way to",
    ],
    "with_article": [
        "where is the",
        "need to find",
        "get to the", 
        "find the",
        "show me the way to",
        "need directions to",
    ],
}

# Entity-based suffixes to attach
ORG_SUFFIXES = ["", "<ORG>"]  # empty = no entity, <ORG> = with ORG entity

def make_patterns(phrases, entity_suffixes):
    """Generate patterns from phrases and entity suffixes."""
    patterns = []
    for phrase in phrases:
        tokens = phrase.split()
        base = [{"LOWER": t} for t in tokens]
        for ent in entity_suffixes:
            if ent == "<ORG>":
                patterns.append(base + [{"ENT_TYPE": "ORG"}])
            else:
                patterns.append(base)
    return patterns

# Build all patterns
all_patterns = []
all_patterns += make_patterns(PHRASE_GROUPS["base"], ORG_SUFFIXES)
all_patterns += make_patterns(PHRASE_GROUPS["with_article"], [""])  # no ORG here

exported_patterns = [
    SpacyIntentPattern(
        intent_name="show_directions",
        patterns=all_patterns,
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0},
    )
]

# Location lexemes for generating entity patterns
LOCATION_LEXEMS = [
    "emergency room",
    "cafeteria", 
    "cardiac care",
    "main entrance",
    "parking garage",
    "elevator",
    "stairs",
    "restroom",
    "bathroom",
    "gift shop",
]

exported_entities = [
    SpacyEntityPattern(
        entity_name="LOCATION",
        patterns=[
            [{"LOWER": token} for token in location.split()]
            for location in LOCATION_LEXEMS
        ],
    )
]