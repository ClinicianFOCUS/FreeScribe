"""
Advanced example demonstrating how to use BatchedLLM for practical applications.

This example shows how to:
1. Generate multiple candidate continuations for a prompt
2. Score each continuation based on custom criteria
3. Select the best continuation based on the scores
4. Implement a simple reranking system

This pattern is useful for applications like:
- Generating high-quality responses for chatbots
- Creating more coherent and relevant text completions
- Implementing a simple form of self-consistency or majority voting

Usage:
    python batched_llm_advanced.py

Requirements:
    - A GGUF model file (e.g., llama-2-7b-chat.Q4_K_M.gguf)
    - The llama-cpp-python package installed
"""

import os
import sys
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add the parent directory to the Python path so we can import the BatchedLLM class
sys.path.append(str(Path(__file__).parent.parent))
from services.batched_llm import BatchedLLM


def score_sequence(sequence: str, criteria: Dict[str, float]) -> float:
    """
    Score a generated sequence based on multiple criteria.
    
    Each criterion is weighted by its importance.
    
    Args:
        sequence: The generated text sequence
        criteria: Dictionary mapping criterion names to their weights
        
    Returns:
        float: The weighted score
    """
    score = 0.0
    
    # Check for coherence (simple heuristic: longer sentences tend to be more coherent)
    if "coherence" in criteria:
        sentences = re.split(r'[.!?]', sequence)
        avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / max(1, len([s for s in sentences if s.strip()]))
        # Normalize: assume ideal length is around 15-20 words
        coherence_score = min(1.0, avg_sentence_length / 20.0)
        score += coherence_score * criteria["coherence"]
    
    # Check for specificity (simple heuristic: presence of numbers, proper nouns, etc.)
    if "specificity" in criteria:
        has_numbers = bool(re.search(r'\d', sequence))
        has_proper_nouns = bool(re.search(r'[A-Z][a-z]+', sequence))
        specificity_score = (has_numbers + has_proper_nouns) / 2.0
        score += specificity_score * criteria["specificity"]
    
    # Check for relevance to keywords
    if "relevance" in criteria and "keywords" in criteria:
        keywords = criteria["keywords"]
        if isinstance(keywords, list):
            keyword_matches = sum(bool(keyword.lower() in sequence.lower()) for keyword in keywords)
            relevance_score = min(1.0, keyword_matches / len(keywords))
            score += relevance_score * criteria["relevance"]
    
    # Check for length (normalize to expected length)
    if "length" in criteria and "target_length" in criteria:
        target_length = criteria["target_length"]
        current_length = len(sequence.split())
        # Score is higher when closer to target length
        length_score = 1.0 - min(1.0, abs(current_length - target_length) / target_length)
        score += length_score * criteria["length"]
    
    return score


def generate_and_select_best(
    model: BatchedLLM,
    prompt: str,
    n_candidates: int = 5,
    n_tokens: int = 100,
    scoring_criteria: Dict[str, float] = None
) -> Tuple[str, List[str], List[float]]:
    """
    Generate multiple candidate continuations and select the best one.
    
    Args:
        model: The BatchedLLM instance
        prompt: The input prompt
        n_candidates: Number of candidate continuations to generate
        n_tokens: Maximum number of tokens to generate per continuation
        scoring_criteria: Dictionary of scoring criteria and their weights
        
    Returns:
        Tuple containing:
        - The best continuation
        - All generated continuations
        - Scores for each continuation
    """
    # Default scoring criteria if none provided
    if scoring_criteria is None:
        scoring_criteria = {
            "coherence": 0.4,
            "specificity": 0.3,
            "length": 0.3,
            "target_length": 50
        }
    
    # Generate multiple continuations in parallel
    continuations, stats, logprobs = model.generate(
        prompt=prompt,
        n_predict=n_tokens,
        n_parallel=n_candidates,
        top_k=40,
        top_p=0.95,
        temp=0.8,  # Higher temperature for more diverse candidates
        seed=int(time.time())  # Random seed based on current time
    )
    
    # Score each continuation
    scores = []
    for continuation in continuations:
        # Extract just the generated part (without the prompt)
        generated_text = continuation[len(prompt):]
        score = score_sequence(generated_text, scoring_criteria)
        scores.append(score)
    
    # Find the best continuation
    best_idx = scores.index(max(scores))
    best_continuation = continuations[best_idx]
    
    return best_continuation, continuations, scores


def main():
    # Configuration
    model_path = "../models/gemma-2-2b-it-Q8_0.gguf"  # Replace with your model path
    
    # Check if the model file exists
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        print("Please update the model_path variable with the correct path to your GGUF model file.")
        return
    
    # Initialize the BatchedLLM
    print(f"Loading model from {model_path}...")
    model = BatchedLLM(
        model_or_path=model_path,
        n_ctx=2048,
        n_threads=4,
        verbose=False
    )
    print("Model loaded successfully")
    
    # Example prompt
    prompt = "Write a short paragraph about climate change that includes specific data:"
    
    # Define scoring criteria with keywords for relevance
    scoring_criteria = {
        "coherence": 0.3,
        "specificity": 0.3,
        "relevance": 0.3,
        "keywords": ["climate", "temperature", "emissions", "carbon", "global"],
        "length": 0.1,
        "target_length": 50
    }
    
    print(f"\nGenerating continuations for prompt: '{prompt}'")
    
    # Generate and select the best continuation
    best, all_continuations, scores = generate_and_select_best(
        model=model,
        prompt=prompt,
        n_candidates=5,
        n_tokens=100,
        scoring_criteria=scoring_criteria
    )
    
    # Display all continuations with their scores
    print("\n=== All Generated Continuations ===")
    for i, (continuation, score) in enumerate(zip(all_continuations, scores)):
        # Extract just the generated part (without the prompt)
        generated_text = continuation[len(prompt):]
        print(f"\nCandidate {i+1} (Score: {score:.4f}):")
        print(f"{generated_text}")
    
    # Display the best continuation
    print("\n=== Best Continuation ===")
    print(f"Score: {max(scores):.4f}")
    print(best[len(prompt):])
    
    # Clean up resources
    model.cleanup()
    print("\nResources cleaned up")


if __name__ == "__main__":
    main()
