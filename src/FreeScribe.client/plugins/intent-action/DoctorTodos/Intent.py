"""
Intent patterns for doctor todo/task recognition.
"""

from services.intent_actions.intents.spacy_recognizer import SpacyIntentPattern, SpacyEntityPattern

# Prescription patterns
prescription_patterns = [
    [{"LEMMA": "prescribe"}, {"OP": "*"}, {"ENT_TYPE": "MEDICATION"}],
    [{"LEMMA": "prescribe"}, {"OP": "*"}, {"ENT_TYPE": "CHEMICAL"}],
    [{"LEMMA": "write"}, {"LOWER": "prescription"}, {"LOWER": "for"}, {"OP": "*"}, {"ENT_TYPE": "MEDICATION"}],
    [{"LEMMA": "start"}, {"OP": "*"}, {"ENT_TYPE": "MEDICATION"}],
    [{"LEMMA": "renew"}, {"OP": "*"}, {"ENT_TYPE": "MEDICATION"}],
    [{"LEMMA": "refill"}, {"OP": "*"}, {"ENT_TYPE": "MEDICATION"}],
    [{"LEMMA": "discontinue"}, {"OP": "*"}, {"ENT_TYPE": "MEDICATION"}],
    [{"LEMMA": "stop"}, {"OP": "*"}, {"ENT_TYPE": "MEDICATION"}],
]

# Scheduling patterns
scheduling_patterns = [
    [{"LEMMA": "schedule"}, {"OP": "*"}, {"LOWER": "follow-up"}],
    [{"LEMMA": "schedule"}, {"OP": "*"}, {"LOWER": "appointment"}],
    [{"LEMMA": "refer"}, {"OP": "*"}, {"ENT_TYPE": "SPECIALIST"}],
    [{"LEMMA": "schedule"}, {"OP": "*"}, {"ENT_TYPE": "DIAGNOSTIC_TEST"}],
    [{"LEMMA": "order"}, {"OP": "*"}, {"ENT_TYPE": "LAB_TEST"}],
    [{"LEMMA": "book"}, {"OP": "*"}, {"ENT_TYPE": "DIAGNOSTIC_TEST"}],
]

# Documentation patterns
documentation_patterns = [
    [{"LEMMA": "document"}, {"OP": "*"}, {"ENT_TYPE": "MEDICAL_RECORD"}],
    [{"LEMMA": "update"}, {"OP": "*"}, {"ENT_TYPE": "MEDICAL_RECORD"}],
    [{"LEMMA": "record"}, {"OP": "*"}, {"ENT_TYPE": "VITAL_SIGN"}],
    [{"LEMMA": "note"}, {"OP": "*"}, {"ENT_TYPE": "SYMPTOM"}],
    [{"LEMMA": "add"}, {"OP": "*"}, {"LOWER": "history"}],
]

exported_patterns = [
    SpacyIntentPattern(
        intent_name="prescribe_medication",
        patterns=prescription_patterns,
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    ),
    SpacyIntentPattern(
        intent_name="schedule_task",
        patterns=scheduling_patterns,
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    ),
    SpacyIntentPattern(
        intent_name="document_medical",
        patterns=documentation_patterns,
        required_entities=[],
        confidence_weights={"pattern_match": 1.0, "entity_match": 0.0}
    )
]

# Medical entities
medications = [
    "metformin", "lisinopril", "atorvastatin", "amlodipine", "metoprolol",
    "omeprazole", "albuterol", "furosemide", "warfarin", "insulin"
]

specialists = [
    "cardiologist", "endocrinologist", "neurologist", "oncologist",
    "psychiatrist", "orthopedist", "dermatologist", "gastroenterologist"
]

diagnostic_tests = [
    "mri", "ct scan", "x-ray", "ultrasound", "mammogram", "colonoscopy",
    "ecg", "echocardiogram", "stress test", "bone density scan"
]

lab_tests = [
    "blood work", "complete blood count", "basic metabolic panel",
    "lipid panel", "hba1c", "thyroid function", "liver function"
]

exported_entities = [
    SpacyEntityPattern(
        entity_name="MEDICATION",
        patterns=[[{"LOWER": word} for word in med.split()] for med in medications]
    ),
    SpacyEntityPattern(
        entity_name="SPECIALIST",
        patterns=[[{"LOWER": word} for word in spec.split()] for spec in specialists]
    ),
    SpacyEntityPattern(
        entity_name="DIAGNOSTIC_TEST",
        patterns=[[{"LOWER": word} for word in test.split()] for test in diagnostic_tests]
    ),
    SpacyEntityPattern(
        entity_name="LAB_TEST",
        patterns=[[{"LOWER": word} for word in test.split()] for test in lab_tests]
    )
]