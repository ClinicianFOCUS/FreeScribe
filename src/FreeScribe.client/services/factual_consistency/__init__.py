"""
.. module:: factual_consistency
   :synopsis: Module for verifying factual consistency between original text and generated summaries.

This module provides a pipeline of different verification methods to ensure accuracy 
in medical note generation. It includes named entity recognition and other verification
techniques to validate that generated summaries accurately reflect the original content.

.. note::
    The module is designed specifically for medical/clinical text verification.

.. warning::
    This is not a general-purpose fact verification system and should only be used
    for medical note generation scenarios.
"""

import logging
from typing import List

from services.factual_consistency.verifiers import ConsistencyPipeline

logger = logging.getLogger(__name__)


# Create a global pipeline instance
pipeline = ConsistencyPipeline()


def find_factual_inconsistency(original_text: str, generated_summary: str) -> List[str]:
    """Check for entities in generated summary that weren't in original text.

    :param original_text: The original transcribed conversation
    :type original_text: str
    :param generated_summary: The generated medical note
    :type generated_summary: str

    :returns: List of entities found in summary but not in original text
    :rtype: List[str]
    
    .. note::
        An empty list means no new entities were found in the summary.
        This doesn't guarantee the summary is 100% accurate - always review carefully.
    """
    results = pipeline.verify(original_text, generated_summary)
    return pipeline.get_inconsistent_entities(results)
