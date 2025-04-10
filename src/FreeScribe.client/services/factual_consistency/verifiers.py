import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

import spacy

logger = logging.getLogger(__name__)


class VerificationMethod(Enum):
    """Enumeration of different verification methods.

    :cvar NER: Named Entity Recognition based verification
    :vartype NER: str

    .. note:: Additional verification methods may be added in future versions.
    """
    NER = "named_entity_recognition"
    # Add more methods as we implement them
    # KEYWORDS = "keyword_matching"
    # SEMANTIC = "semantic_similarity"
    # NUMERICAL = "numerical_consistency"


@dataclass
class VerificationResult:
    """Data class to hold verification results.

    :param method: The verification method used
    :type method: VerificationMethod
    :param inconsistent_items: List of inconsistent items found
    :type inconsistent_items: List[str]
    :default inconsistent_items: []

    .. note:: If inconsistent_items is empty, no inconsistencies were found.
    """
    method: VerificationMethod
    inconsistent_items: List[str] = field(default_factory=list)


class ConsistencyVerifier(ABC):
    """Abstract base class for consistency verifiers.

    This class defines the interface for all concrete verification implementations.
    Subclasses must implement the verify() method.

    .. note:: All verifiers should be thread-safe as they may be used concurrently.
    """

    @abstractmethod
    def verify(self, original_text: str, generated_summary: str) -> VerificationResult:
        """Check for entities in summary that weren't in original text.

        :param original_text: The original conversation text
        :type original_text: str
        :param generated_summary: The generated medical note
        :type generated_summary: str

        :returns: Verification result with any new entities found
        :rtype: VerificationResult

        .. note::
            This is a basic check - it only looks for entities that appear
            in the summary but not the original text. It doesn't verify
            the accuracy or appropriateness of the summary content.
        """
        pass


class NERVerifier(ConsistencyVerifier):
    """Named Entity Recognition based verifier.

    This verifier uses spaCy's NER capabilities to compare medical entities
    between original text and generated summaries.

    :ivar nlp: The spaCy language model for medical text processing
    :vartype nlp: spacy.Language

    .. note:: The model is automatically downloaded if not present.

    .. warning:: The 'en_core_web_trf' model requires significant memory resources.
    """
    NLP_MODEL = "en_core_sci_md"

    def __init__(self):
        try:
            self.nlp = spacy.load(self.NLP_MODEL)
        except (OSError, ImportError, ValueError):
            logger.error(f"Error loading spaCy model {self.NLP_MODEL}: {e}")
            logger.info(f"Downloading spaCy model {self.NLP_MODEL}...")
            spacy.cli.download(self.NLP_MODEL)
            try:
                self.nlp = spacy.load(self.NLP_MODEL)
            except Exception as load_error:
                raise EnvironmentError(f"Failed to load {self.NLP_MODEL} after downloading") from load_error

    def verify(self, original_text: str, generated_summary: str) -> VerificationResult:
        """
        Check for entities in summary that weren't in original text.

        :param original_text: The original conversation text
        :type original_text: str
        :param generated_summary: The generated medical note
        :type generated_summary: str

        :returns: VerificationResult containing:
            - inconsistent_items: List of new entities found in summary
            - method: The verification method used

        .. note:: This helps identify potential additions in the summary that
                  weren't mentioned in the original conversation.
        """
        if not generated_summary or not original_text:
            return VerificationResult(method=VerificationMethod.NER)

        # Process both texts with spaCy
        original_doc = self.nlp(original_text.lower())
        summary_doc = self.nlp(generated_summary.lower())

        # Extract named entities from both texts
        original_entities = {ent.text for ent in original_doc.ents}
        summary_entities = {ent.text for ent in summary_doc.ents}
        logger.debug(f"summary entities: {[(x.text, x.label_) for x in summary_doc.ents]}")

        # Find entities that appear in summary but not in original text
        inconsistent_entities = list(summary_entities - original_entities)

        return VerificationResult(
            inconsistent_items=inconsistent_entities,
            method=VerificationMethod.NER
        )


class ConsistencyPipeline:
    """Pipeline for running multiple consistency verifications.

    This class orchestrates the execution of multiple verification methods
    and aggregates their results.

    :ivar verifiers: Dictionary mapping verification methods to their implementations
    :vartype verifiers: Dict[VerificationMethod, ConsistencyVerifier]

    .. note:: New verification methods can be added by extending the verifiers dictionary.

    .. warning:: The pipeline assumes all verifiers are independent and can be run in any order.
    """

    def __init__(self):
        self.verifiers: Dict[VerificationMethod, ConsistencyVerifier] = {
            VerificationMethod.NER: NERVerifier(),
            # Add more verifiers as we implement them
        }
        
    def verify(self, original_text: str, generated_summary: str) -> Dict[VerificationMethod, VerificationResult]:
        """
        Check summary against original text using available verification methods.

        :param original_text: The original conversation text
        :type original_text: str
        :param generated_summary: The generated medical note
        :type generated_summary: str

        :returns: Dictionary mapping verification methods to their results
        :rtype: Dict[VerificationMethod, VerificationResult]

        .. note:: Currently only checks for new entities, but could be extended
                  with additional verification methods in the future.
        """
        results = {}
        for method, verifier in self.verifiers.items():
            try:
                results[method] = verifier.verify(original_text, generated_summary)
            except Exception as e:
                logger.error(f"Error in {method.value} verification: {str(e)}")
                # Create a failed result
                results[method] = VerificationResult(
                    inconsistent_items=[f"Verification failed: {str(e)}"],
                    method=method
                )
        return results

    def get_inconsistent_entities(self, results: Dict[VerificationMethod, VerificationResult]) -> List[str]:
        """
        Get all new entities found in summary across verification methods.

        :param results: Dictionary of verification results from each method
        :type results: Dict[VerificationMethod, VerificationResult]

        :returns: List of entities found in summary but not in original text
        :rtype: List[str]

        .. note:: These are potential additions to review, not necessarily errors.
                  Some new entities may be appropriate inferences by the AI.
        """
        if not results:
            return ["No verification methods available"]

        # Collect all issues
        all_issues = []
        for result in results.values():
            all_issues.extend(result.inconsistent_items)

        return all_issues
