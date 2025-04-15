import pytest
from unittest.mock import Mock, patch
from spacy.language import Language
from spacy.tokens import Doc
from services.whisper_hallucination_cleaner import (
    WhisperHallucinationCleaner,
    COMMON_HALUCINATIONS,
    SIMILARITY_THRESHOLD,
    SPACY_MODEL_NAME,
    HallucinationCleanerException,
    default_logger,
)
import spacy


@pytest.fixture(scope="session")
def spacy_model():
    """Create a shared spaCy model for all tests.
    
    :returns: A loaded spaCy model
    :rtype: spacy.language.Language
    """
    return spacy.load(SPACY_MODEL_NAME)


@pytest.fixture
def mock_nlp():
    """Create a mock spaCy model."""
    class MockSentence:
        def __init__(self, text):
            self.text = text
            
    class MockDoc:
        def __init__(self, text):
            self.text = text
            self.sents = [MockSentence(text)]
            
        def __len__(self):
            return len(self.text.split())
            
        def similarity(self, other):
            return 0.0  # Return low similarity by default
            
    mock = Mock(spec=Language)
    mock.return_value = MockDoc("Some text")
    return mock


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock()


@pytest.fixture
def custom_hallucinations():
    """Create a custom list of hallucinations."""
    return ["test hallucination", "another test"]


@pytest.fixture
def cleaner(spacy_model):
    """Create a WhisperHallucinationCleaner instance for testing.

    :returns: A configured WhisperHallucinationCleaner instance
    :rtype: WhisperHallucinationCleaner
    """
    return WhisperHallucinationCleaner(
        similarity_threshold=SIMILARITY_THRESHOLD,
        nlp=spacy_model
    )


@pytest.fixture
def strict_cleaner(spacy_model):
    """Create a WhisperHallucinationCleaner instance with strict threshold.
    
    :returns: A WhisperHallucinationCleaner with high similarity threshold
    :rtype: WhisperHallucinationCleaner
    """
    return WhisperHallucinationCleaner(
        similarity_threshold=0.95,
        nlp=spacy_model
    )


@pytest.fixture
def lenient_cleaner(spacy_model):
    """Create a WhisperHallucinationCleaner instance with lenient threshold.
    
    :returns: A WhisperHallucinationCleaner with low similarity threshold
    :rtype: WhisperHallucinationCleaner
    """
    return WhisperHallucinationCleaner(
        similarity_threshold=0.5,
        nlp=spacy_model
    )


@pytest.fixture
def similar_phrases():
    """Provide test phrases that should be detected as similar to hallucinations.
    
    :returns: List of phrases similar to hallucinations
    :rtype: list[str]
    """
    return [
        "thanks for your attention",
        "thank you for listening",
        "I'll see you in the next video",
        "Thanks for watching, and I'll see you in the next video, and I'll see you in the next video.",
    ]


@pytest.fixture
def dissimilar_phrases():
    """Provide test phrases that should not be detected as similar to hallucinations.
    
    :returns: List of phrases not similar to hallucinations
    :rtype: list[str]
    """
    return [
        "the weather is nice today",
        "please pass the salt",
        "what time is the meeting"
    ]


@pytest.fixture
def test_input_text():
    """Provide test input text."""
    return "Some text"


@pytest.fixture
def test_hallucination():
    """Provide a single test hallucination."""
    return "thank you"


@pytest.mark.parametrize("test_case", [
    {
        "name": "default threshold",
        "expected": SIMILARITY_THRESHOLD
    }
])
def test_initialization(cleaner, test_case):
    """Test the initialization of the cleaner.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    :param test_case: Dictionary containing test case data
    :type test_case: dict
    """
    assert cleaner.similarity_threshold == test_case["expected"]
    assert isinstance(cleaner.hallucinations, set)
    expected_content = {cleaner._normalize_text(h) for h in COMMON_HALUCINATIONS}
    assert cleaner.hallucinations == expected_content


def test_nlp_loading(cleaner):
    """Test that the spacy model loads and can process text.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    """
    assert cleaner.nlp is not None
    doc = cleaner.nlp("Test sentence.")
    assert len(list(doc.sents)) == 1


@pytest.mark.parametrize("test_case", [
    {
        "name": "hallucinations content check",
        "expected": lambda c: {c._normalize_text(h) for h in COMMON_HALUCINATIONS}
    }
])
def test_initialization_content_param(cleaner, test_case):
    """Test the content of hallucinations set.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    :param test_case: Dictionary containing test case data
    :type test_case: dict
    """
    assert cleaner.hallucinations == test_case["expected"](cleaner)


def test_initialization_threshold(cleaner):
    """Test the initialization of similarity threshold.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    """
    assert cleaner.similarity_threshold == SIMILARITY_THRESHOLD


def test_initialization_type(cleaner):
    """Test the type of hallucinations set.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    """
    assert isinstance(cleaner.hallucinations, set)


def test_initialization_content(cleaner):
    """Test the content of hallucinations set.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    """
    expected = {cleaner._normalize_text(h) for h in COMMON_HALUCINATIONS}
    assert cleaner.hallucinations == expected


def test_nlp_loading_not_none(cleaner):
    """Test that the spacy model loads and is not None.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    """
    assert cleaner.nlp is not None


def test_nlp_loading_can_process(cleaner):
    """Test that the loaded spacy model can process text.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    """
    doc = cleaner.nlp("Test sentence.")
    assert len(list(doc.sents)) == 1


@pytest.mark.parametrize("test_case", [
    {
        "name": "exact match",
        "input": "thank you",
        "should_match": True
    },
    {
        "name": "similar match",
        "input": "thanks a lot",
        "should_match": True
    },
    {
        "name": "different text",
        "input": "the quick brown fox jumps over the lazy dog",
        "should_match": False
    }
])
@pytest.mark.hallucination
def test_is_similar_to_hallucination_cases(cleaner, test_case):
    """Test similarity checking against hallucinations.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    :param test_case: Dictionary containing test case data
    :type test_case: dict
    """
    result = cleaner._is_similar_to_hallucination(test_case["input"])
    assert result == test_case["should_match"]


@pytest.mark.parametrize("test_case", [
    {
        "name": "multiple sentences",
        "input": "First sentence. Second sentence. Third sentence.",
        "expected_count": 3
    },
    {
        "name": "empty text",
        "input": "",
        "expected_count": 0
    },
    {
        "name": "mixed punctuation",
        "input": "Sentence one! Sentence two? Sentence three.",
        "expected_count": 3
    }
])
@pytest.mark.sentences
def test_split_into_sentences_count(cleaner, test_case):
    """Test sentence splitting functionality - count check.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    :param test_case: Dictionary containing test case data
    :type test_case: dict
    """
    sentences = cleaner._split_into_sentences(test_case["input"])
    assert len(sentences) == test_case["expected_count"]


@pytest.mark.parametrize("test_case", [
    {
        "name": "first of multiple periods",
        "input": "First sentence. Second sentence. Third sentence.",
        "expected": "First sentence."
    },
    {
        "name": "first with mixed punctuation",
        "input": "Sentence one! Sentence two? Sentence three.",
        "expected": "Sentence one!"
    }
])
@pytest.mark.sentences
def test_split_into_sentences_first(cleaner, test_case):
    """Test sentence splitting functionality - first sentence check.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    :param test_case: Dictionary containing test case data
    :type test_case: dict
    """
    sentences = cleaner._split_into_sentences(test_case["input"])
    assert sentences[0].strip() == test_case["expected"]


@pytest.mark.parametrize("test_case", [
    {
        "name": "last of multiple periods",
        "input": "First sentence. Second sentence. Third sentence.",
        "expected": "Third sentence."
    },
    {
        "name": "last with mixed punctuation",
        "input": "Sentence one! Sentence two? Sentence three.",
        "expected": "Sentence three."
    }
])
@pytest.mark.sentences
def test_split_into_sentences_last(cleaner, test_case):
    """Test sentence splitting functionality - last sentence check.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    :param test_case: Dictionary containing test case data
    :type test_case: dict
    """
    sentences = cleaner._split_into_sentences(test_case["input"])
    assert sentences[-1].strip() == test_case["expected"]


@pytest.mark.parametrize("test_case", [
    {
        "name": "empty text",
        "input": "",
        "expected": ""
    },
    {
        "name": "text without hallucinations",
        "input": "This is a normal text without any hallucinations.",
        "expected": "This is a normal text without any hallucinations."
    },
    {
        "name": "text with hallucination",
        "input": "This is a normal sentence. Thank you for watching.",
        "expected": "This is a normal sentence."
    },
    {
        "name": "text with multiple hallucinations",
        "input": "Thank you. This is a normal sentence. Thanks for watching.",
        "expected": "This is a normal sentence."
    }
])
@pytest.mark.cleaner
def test_global_hallucination_cleaner_cases(cleaner, test_case):
    """Test the global hallucination cleaner with various text inputs.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    :param test_case: Dictionary containing test case data
    :type test_case: dict
    """
    result = cleaner.clean_text(test_case["input"])
    assert result == test_case["expected"]


@pytest.mark.parametrize("phrase", [
    "thanks for your attention",
    "thank you for listening",
    "I'll see you in the next video",
    "Thanks for watching, and I'll see you in the next video, and I'll see you in the next video.",
])
@pytest.mark.hallucination
def test_similar_phrases(cleaner, phrase):
    """Test that phrases similar to hallucinations are detected.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    :param phrase: A phrase that should be detected as similar
    :type phrase: str
    """
    assert cleaner._is_similar_to_hallucination(phrase)


@pytest.mark.parametrize("phrase", [
    "the weather is nice today",
    "please pass the salt",
    "what time is the meeting"
])
@pytest.mark.hallucination
def test_dissimilar_phrases(cleaner, phrase):
    """Test that dissimilar phrases are not detected as hallucinations.
    
    :param cleaner: The WhisperHallucinationCleaner fixture
    :type cleaner: WhisperHallucinationCleaner
    :param phrase: A phrase that should not be detected as similar
    :type phrase: str
    """
    assert not cleaner._is_similar_to_hallucination(phrase)


@pytest.fixture
def mock_spacy_model():
    """Fixture that creates a mock spaCy model.
    
    :returns: A mock spaCy model with required attributes
    """
    class MockDoc:
        def __init__(self, text):
            self.text = text
            self.sents = [self]
            
    class MockModel:
        def __init__(self):
            pass
            
        def __call__(self, text):
            return MockDoc(text)
            
    return MockModel()


@pytest.fixture
def successful_init_mocks(monkeypatch, mock_spacy_model):
    """Fixture that mocks successful model initialization.
    
    :param monkeypatch: pytest's monkeypatch fixture
    :type monkeypatch: pytest.MonkeyPatch
    :param mock_spacy_model: Mock spaCy model
    """
    def mock_spacy_load(model_path):
        return mock_spacy_model
    
    monkeypatch.setattr(spacy, "load", mock_spacy_load)


@pytest.fixture
def mock_successful_initialize(monkeypatch):
    """Fixture that mocks successful model initialization.
    
    :param monkeypatch: pytest's monkeypatch fixture
    :type monkeypatch: pytest.MonkeyPatch
    :returns: Tuple of (cleaner, initialize_called flag)
    """
    cleaner = WhisperHallucinationCleaner()
    initialize_called = [False]  # Using list to allow modification in closure
    
    def mock_initialize_model():
        initialize_called[0] = True
        return None
    
    monkeypatch.setattr(cleaner, "initialize_model", mock_initialize_model)
    return cleaner, initialize_called[0], initialize_called


def test_nlp_property_calls_initialize(mock_successful_initialize):
    """Test that nlp property triggers initialization.
    
    :param mock_successful_initialize: Tuple of (cleaner, initialize_called flag, flag_ref)
    """
    cleaner, _, flag_ref = mock_successful_initialize
    _ = cleaner.nlp
    assert flag_ref[0]


def test_failed_initialization(failed_init_mocks):
    """Test failed model initialization.
    
    :param failed_init_mocks: Mocks for failed initialization
    """
    cleaner = WhisperHallucinationCleaner()
    error = cleaner.initialize_model()
    
    assert "Failed to initialize spaCy model" in error
    assert cleaner._nlp is None
    assert cleaner._hallucination_docs is None


@pytest.fixture
def mock_failed_initialize(monkeypatch):
    """Fixture that mocks failed model initialization.
    
    :param monkeypatch: pytest's monkeypatch fixture
    :type monkeypatch: pytest.MonkeyPatch
    :returns: Tuple of (cleaner, error message)
    """
    cleaner = WhisperHallucinationCleaner()
    error_message = "Test initialization error"
    
    def mock_initialize_model():
        return error_message
    
    monkeypatch.setattr(cleaner, "initialize_model", mock_initialize_model)
    return cleaner, error_message


def test_nlp_property_propagates_error(mock_failed_initialize):
    """Test that nlp property propagates initialization errors.
    
    :param mock_failed_initialize: Tuple of (cleaner, error message)
    """
    cleaner, error_message = mock_failed_initialize
    
    with pytest.raises(RuntimeError) as exc_info:
        _ = cleaner.nlp
    
    assert error_message in str(exc_info.value)


@pytest.fixture
def failed_init_mocks(monkeypatch):
    """Fixture that mocks failed model initialization.
    
    :param monkeypatch: pytest's monkeypatch fixture
    :type monkeypatch: pytest.MonkeyPatch
    """
    def mock_spacy_load(model_path):
        raise HallucinationCleanerException("Mock load failure")
    
    monkeypatch.setattr(spacy, "load", mock_spacy_load)


def test_successful_initialization(successful_init_mocks, mock_spacy_model):
    """Test successful model initialization.
    
    :param successful_init_mocks: Mocks for successful initialization
    :param mock_spacy_model: Mock spaCy model
    """
    cleaner = WhisperHallucinationCleaner()
    error = cleaner.initialize_model()
    
    assert error is None
    assert cleaner._nlp is not None
    assert cleaner._hallucination_docs is not None


@pytest.fixture
def initialized_cleaner(successful_init_mocks, mock_spacy_model):
    """Fixture that provides an initialized cleaner.
    
    :param successful_init_mocks: Mocks for successful initialization
    :param mock_spacy_model: Mock spaCy model
    :returns: Initialized WhisperHallucinationCleaner
    """
    cleaner = WhisperHallucinationCleaner()
    cleaner.initialize_model()
    return cleaner


def test_unload_model_clears_references(initialized_cleaner):
    """Test that unload_model clears model references.
    
    :param initialized_cleaner: Initialized cleaner fixture
    """
    # Verify cleaner is initialized
    assert initialized_cleaner._nlp is not None
    assert initialized_cleaner._hallucination_docs is not None
    
    # Unload the model
    initialized_cleaner.unload_model()
    
    # Verify references are cleared
    assert initialized_cleaner._nlp is None
    assert initialized_cleaner._hallucination_docs is None


def test_unload_model_can_be_called_multiple_times(initialized_cleaner):
    """Test that unload_model can be called safely multiple times.
    
    :param initialized_cleaner: Initialized cleaner fixture
    """
    # First unload
    initialized_cleaner.unload_model()
    
    # Second unload should not raise errors
    initialized_cleaner.unload_model()
    
    # References should still be None
    assert initialized_cleaner._nlp is None
    assert initialized_cleaner._hallucination_docs is None


def test_unload_model_can_be_called_before_initialization():
    """Test that unload_model can be called safely before initialization."""
    cleaner = WhisperHallucinationCleaner()
    
    # Should not raise errors
    cleaner.unload_model()
    
    # References should be None
    assert cleaner._nlp is None
    assert cleaner._hallucination_docs is None


def test_cleaner_with_custom_model_input_text(mock_nlp, test_input_text):
    """Test that cleaner processes input text with custom model."""
    cleaner = WhisperHallucinationCleaner(nlp=mock_nlp)
    result = cleaner.clean_text(test_input_text)
    assert result == test_input_text
    mock_nlp.assert_any_call(test_input_text)


def test_cleaner_with_custom_model_hallucination(mock_nlp, test_hallucination):
    """Test that cleaner processes hallucination with custom model."""
    cleaner = WhisperHallucinationCleaner(nlp=mock_nlp)
    cleaner.clean_text("Some text")
    mock_nlp.assert_any_call(test_hallucination)


@pytest.mark.parametrize("hallucination", [
    "thank you",
    "thanks for watching",
    "see you next time",
    "hello everyone welcome to my channel"
])
def test_cleaner_with_custom_model_specific_hallucinations(mock_nlp, hallucination):
    """Test that cleaner processes specific hallucination phrases."""
    cleaner = WhisperHallucinationCleaner(nlp=mock_nlp)
    cleaner.clean_text("Some text")
    mock_nlp.assert_any_call(hallucination)


def test_cleaner_with_custom_logger(mock_logger):
    """Test cleaner with injected logger."""
    cleaner = WhisperHallucinationCleaner(logger=mock_logger)
    cleaner.clean_text("Some text")
    mock_logger.debug.assert_called()


def test_cleaner_with_custom_hallucinations(custom_hallucinations):
    """Test cleaner with custom hallucinations list."""
    cleaner = WhisperHallucinationCleaner(hallucinations=custom_hallucinations)
    assert len(cleaner.hallucinations) == len(custom_hallucinations)
    assert all(h in cleaner.hallucinations for h in custom_hallucinations)


def test_cleaner_with_custom_similarity_threshold():
    """Test cleaner with custom similarity threshold."""
    threshold = 0.8
    cleaner = WhisperHallucinationCleaner(similarity_threshold=threshold)
    assert cleaner.similarity_threshold == threshold


def test_cleaner_with_custom_model_path():
    """Test cleaner with custom spaCy model name."""
    model_name = SPACY_MODEL_NAME
    cleaner = WhisperHallucinationCleaner(spacy_model_name=model_name)
    assert cleaner.spacy_model_name == model_name


def test_cleaner_with_all_custom_dependencies(mock_nlp, mock_logger, custom_hallucinations):
    """Test cleaner with all dependencies customized."""
    cleaner = WhisperHallucinationCleaner(
        similarity_threshold=0.8,
        spacy_model_name=SPACY_MODEL_NAME,
        hallucinations=custom_hallucinations,
        nlp=mock_nlp,
        logger=mock_logger
    )
    
    # Verify all customizations are applied
    assert cleaner.similarity_threshold == 0.8
    assert cleaner.spacy_model_name == SPACY_MODEL_NAME
    assert len(cleaner.hallucinations) == len(custom_hallucinations)
    assert cleaner._nlp == mock_nlp
    assert cleaner.logger == mock_logger


def test_cleaner_with_default_dependencies():
    """Test cleaner with default dependencies."""
    cleaner = WhisperHallucinationCleaner()
    
    # Verify default values are used
    assert cleaner.similarity_threshold == 0.95  # Default from module
    assert cleaner.spacy_model_name == SPACY_MODEL_NAME  # Default from module
    assert cleaner._nlp is None  # Should be None initially
    assert cleaner.logger is not None  # Should have default logger


@pytest.fixture
def mock_settings():
    """Create a mock settings object with hallucination cleaning setting."""
    class MockSettings:
        def __init__(self):
            self.editable_settings = {}
            self.editable_settings_entries = {}
            
    return MockSettings()


@pytest.fixture
def mock_settings_entry():
    """Create a mock settings entry that can be get/set."""
    class MockEntry:
        def __init__(self, value=True):
            self._value = value
            
        def get(self):
            return self._value
            
        def set(self, value):
            self._value = value
            
    return MockEntry()


def test_unload_model_when_hallucination_cleaning_disabled(initialized_cleaner, mock_settings, mock_settings_entry):
    """Test that unload_model is called when hallucination cleaning is disabled.
    
    :param initialized_cleaner: Initialized cleaner fixture
    :param mock_settings: Mock settings object
    :param mock_settings_entry: Mock settings entry object
    """
    from UI.SettingsWindowUI import SettingsKeys
    
    # Setup mock settings
    mock_settings.editable_settings[SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value] = True
    mock_settings.editable_settings_entries[SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value] = mock_settings_entry
    
    # Verify cleaner is initialized
    assert initialized_cleaner._nlp is not None
    assert initialized_cleaner._hallucination_docs is not None
    
    # Simulate disabling hallucination cleaning
    mock_settings_entry._value = False
    
    # Create mock UI and call load_hallucination_cleaner
    class MockUI:
        def __init__(self, settings, cleaner):
            self.settings = settings
            self.cleaner = cleaner
            
        def load_hallucination_cleaner(self):
            current_enabled = self.settings.editable_settings.get(SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value)
            setting_entry = self.settings.editable_settings_entries.get(SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value)
            new_enabled = setting_entry.get() if setting_entry else None
            
            if new_enabled is not None and not new_enabled:
                self.cleaner.unload_model()
    
    ui = MockUI(mock_settings, initialized_cleaner)
    ui.load_hallucination_cleaner()
    
    # Verify model was unloaded
    assert initialized_cleaner._nlp is None
    assert initialized_cleaner._hallucination_docs is None 