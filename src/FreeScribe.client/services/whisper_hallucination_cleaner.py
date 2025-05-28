"""Whisper Hallucination Cleaner.

This module provides functionality to clean common hallucinations from Whisper transcriptions.
It uses spaCy's vector similarity to detect and remove common phrases that Whisper tends to
hallucinate at the end of transcriptions.

Example:
    >>> from services.whisper_hallucination_cleaner import hallucination_cleaner
    >>> text = "This is a real transcription. Thanks for watching!"
    >>> cleaned = hallucination_cleaner.clean_text(text)
    >>> print(cleaned)
    'This is a real transcription.'
"""
import threading
from tkinter import messagebox
from typing import List, Optional
import string
import spacy
import logging
from spacy.language import Language
from spacy.tokens import Doc
import os

from UI.LoadingWindow import LoadingWindow
from UI.SettingsConstant import SettingsKeys, FeatureToggle

# Create a punctuation string without apostrophe
punct_without_apostrophe = string.punctuation.replace("'", "")

# Default logger
default_logger = logging.getLogger(__name__)

class HallucinationCleanerException(Exception):
    """Exception raised for errors in the hallucination cleaner."""
    pass


COMMON_HALUCINATIONS = [
    "thank you",
    "thank y'all",
    "thanks mate",
    "thanks a lot",
    "thank you all",
    "thank you bye",
    "thank you for",
    "thank you sir",
    "thank you too",
    "thanks so much",
    "thank you again",
    "thank you thank",
    "thanks everyone",
    "thanks very much",
    "see you next time",
    "thank you bye bye",
    "thank you so much",
    "it's no good to me",
    "see you next video",
    "thank you everyone",
    "thank you very much",
    "thanks for watching",
    "he was gonna catch it",
    "thank you all so much",
    "i'll see you next time",
    "thank you for watching",
    "see you in the next one",
    "thank you all very much",
    "bye ladies and gentlemen",
    "thanks for your watching",
    "see you in the next video",
    "subtitles by steamteamextra",
    "thank you for your watching",
    "i'll see you in the next video",
    "i'm not sure what i'm doing here",
    "thank you very much for watching",
    "hello everyone welcome to my channel",
    "subtitles by the amara org community",
    "thank you very much thank you very much",
    "like comment and subscribe to the channel",
    "don't forget to like comment and subscribe to the channel",
    "sorry don't ask me if i asked about this question right and i mean the lightening",
]

# Calculate max length based on tokens instead of characters for more accurate comparison
MAX_SENTENCE_LENGTH = max(len(hallucination.split()) for hallucination in COMMON_HALUCINATIONS)
SIMILARITY_THRESHOLD = 0.95
SPACY_MODEL_NAME = "en_core_web_md"


class WhisperHallucinationCleaner:
    """A class to clean common hallucinations from Whisper transcriptions.
    
    This class uses spaCy's vector similarity to detect and remove common phrases
    that Whisper tends to hallucinate, particularly at the end of transcriptions.
    
    :param similarity_threshold: The minimum similarity ratio (0-1) between a sentence
                               and a hallucination to consider it a match
    :param spacy_model_name: Name of the spaCy model to use
    :param hallucinations: List of hallucination phrases to check against
    :param nlp: Optional pre-configured spaCy model
    :param logger: Logger instance for debugging
    :type similarity_threshold: float
    :type spacy_model_name: str
    :type hallucinations: List[str]
    :type nlp: Optional[Language]
    :type logger: logging.Logger
    """
    
    def __init__(
        self,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        spacy_model_name: str = SPACY_MODEL_NAME,
        hallucinations: List[str] = COMMON_HALUCINATIONS,
        nlp: Optional[Language] = None,
        logger: logging.Logger = default_logger
    ):
        """Initialize the cleaner with configurable dependencies.
        
        :param similarity_threshold: The minimum similarity ratio (0-1)
        :param spacy_model_name: Name of the spaCy model to use
        :param hallucinations: List of hallucination phrases to check against
        :param nlp: Optional pre-configured spaCy model
        :param logger: Logger instance for debugging
        """
        self.logger = logger
        self.similarity_threshold = similarity_threshold
        self.spacy_model_name = spacy_model_name
        self._trans_table = str.maketrans(punct_without_apostrophe, ' ' * len(punct_without_apostrophe))
        self.hallucinations = {self._normalize_text(h) for h in hallucinations}
        self._nlp = nlp
        self._hallucination_docs = None
        
    def initialize_model(self) -> Optional[str]:
        """Initialize the spaCy model proactively.
        
        This method should be called when the hallucination cleaning feature is enabled
        in settings. It downloads and loads the model if necessary.
        
        :returns: Error message if initialization fails, None if successful
        :rtype: Optional[str]
        """
        if self._nlp is not None:
            return None
            
        try:
            self._nlp = spacy.load(self.spacy_model_name)
            # Pre-process hallucination docs
            self._hallucination_docs = [
                self._nlp(h) for h in sorted(self.hallucinations)
            ]
            return None
        except IOError as e:
            return f"Failed to load spaCy model. {e}"
        except Exception as e:
            error_msg = f"Failed to initialize spaCy model: {str(e)}"
            self.logger.exception(error_msg)
            return error_msg

    def unload_model(self):
        """Unload the spaCy model and free resources."""
        self._nlp = None
        self._hallucination_docs = None
        self.logger.info("Unloaded spaCy model")
        
    @property
    def nlp(self) -> Language:
        """Lazy load the spacy model.
        
        :returns: The loaded spaCy model
        :rtype: spacy.language.Language
        :raises RuntimeError: If the spaCy model fails to download
        """
        if self._nlp is None:
            if error := self.initialize_model():
                raise RuntimeError(error)
        return self._nlp
    
    @property
    def hallucination_docs(self) -> List[Doc]:
        """Lazy load the hallucination docs.
        
        :returns: List of processed spaCy docs for each hallucination
        :rtype: list[spacy.tokens.Doc]
        """
        if self._hallucination_docs is None:
            # Process all hallucinations and store their docs
            self._hallucination_docs = [
                self.nlp(h) for h in sorted(COMMON_HALUCINATIONS)  # Use original text for semantic similarity
            ]
        return self._hallucination_docs
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text by removing punctuation and extra whitespace.
        
        :param text: The text to normalize
        :type text: str
        :returns: Normalized text with punctuation removed and whitespace normalized
        :rtype: str
        """
        # Remove punctuation and normalize whitespace
        text = text.strip().lower()
        # remove all punctuation
        text = text.translate(self._trans_table)
        text = ' '.join(t for t in text.split() if t.isalnum())
        self.logger.debug(f"Normalized text: {text}")
        return text
    
    def _is_similar_to_hallucination(self, sentence: str) -> bool:
        """Check if a sentence is similar to any known hallucination using vector similarity.
        
        :param sentence: The sentence to check for hallucination similarity
        :type sentence: str
        :returns: True if the sentence is similar to a known hallucination, False otherwise
        :rtype: bool
        """
        if not sentence:
            return False

        # Normalize for exact matching
        normalized = self._normalize_text(sentence)
        # First check for exact matches (case insensitive)
        if any(h in normalized for h in self.hallucinations):
            self.logger.debug(f"Sentence contains a hallucination: {normalized}")
            return True
            
        # Process the original sentence for semantic similarity
        doc = self.nlp(sentence)
        
        # Longer sentences are less likely to be hallucinations
        if len(doc) > MAX_SENTENCE_LENGTH * 1.5:
            return False
            
        # Use pre-processed hallucination docs for similarity check
        result = any(doc.similarity(h_doc) >= self.similarity_threshold 
                  for h_doc in self.hallucination_docs)
        if result:
            self.logger.debug(f"Sentence is similar to hallucination: {sentence}")
        return result
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using spacy.
        
        :param text: The text to split into sentences
        :type text: str
        :returns: List of sentences
        :rtype: List[str]
        """
        if not text:
            return []
            
        # Process the text with spacy
        doc = self.nlp(text)
        # Get sentences and preserve their original text
        return [sent.text.strip() for sent in doc.sents]
    
    def clean_text(self, text: str) -> str:
        """Clean the text by removing sentences similar to known hallucinations.
        
        :param text: The text to clean
        :type text: str
        :returns: Cleaned text with hallucination sentences removed
        :rtype: str

        Example:
            >>> cleaner = WhisperHallucinationCleaner()
            >>> text = "This is a real transcription. Thanks for watching!"
            >>> cleaned = cleaner.clean_text(text)
            >>> print(cleaned)
            'This is a real transcription.'
        """
        if not text:
            return text
            
        sentences = self._split_into_sentences(text)
        cleaned_sentences = [s for s in sentences if not self._is_similar_to_hallucination(s)]
        
        # Join sentences back together with a single space, since each sentence already has its punctuation
        result = ' '.join(s.strip() for s in cleaned_sentences)
        self.logger.debug(f"Cleaned text: {result}")
        return result


def load_hallucination_cleaner_model(root, settings) -> None:
    """
    Loads or unloads the hallucination cleaner based on settings.

    The logic handles two scenarios:
    1. Application startup: new_value is None, use current setting
    2. Settings change: new_value exists, compare with previous setting
    """
    # Get current enabled state from settings
    current_enabled = settings.editable_settings.get(SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value) and FeatureToggle.HALLUCINATION_CLEANING

    # Get new value from settings panel if it exists
    setting_entry = settings.editable_settings_entries.get(SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value) and FeatureToggle.HALLUCINATION_CLEANING
    new_enabled = setting_entry.get() if setting_entry else None

    default_logger.info(f"Hallucination cleaner - Current: {current_enabled}, New: {new_enabled}")

    # Determine if we should initialize the model
    should_initialize = (
        # Case 1: App startup - initialize if currently enabled
        (new_enabled is None and current_enabled) or
        # Case 2: Settings changed - initialize if newly enabled
        (new_enabled is not None and new_enabled and not current_enabled)
    )

    # Determine if we should unload the model
    should_unload = (
        # Only unload if setting was explicitly changed to disabled
        new_enabled is not None and not new_enabled
    )

    # Launch initialization/unloading in a separate thread
    threading.Thread(target=_initialize_spacy_model,
                     args=(root, should_initialize, should_unload),
                     daemon=True).start()


def _initialize_spacy_model(root, is_init_model: bool, is_unload_model: bool):
    """
    Initializes or unloads the spaCy model for hallucination cleaning.

    Args:
        is_init_model (bool): True to initialize the model
        is_unload_model (bool): True to unload the model
    """
    if is_init_model:
        loading_window = LoadingWindow(
            root,
            "Loading SpaCy Model",
            "Setting up spaCy model for hallucination cleaning. Please wait...",
            note_text="Note: This may take a few minutes on first run."
        )
        error = hallucination_cleaner.initialize_model()
        loading_window.destroy()

        if error:
            messagebox.showerror(
                "SpaCy Model Error",
                f"Failed to initialize spaCy model for hallucination cleaning: {error}\n\n"
                "Hallucination cleaning will be disabled."
            )
    if is_unload_model:
        hallucination_cleaner.unload_model()


# Initialize the hallucination cleaner with default settings
hallucination_cleaner = WhisperHallucinationCleaner()
