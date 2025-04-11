"""
Simple example demonstrating how to use the BatchedLLM class for parallel text generation.

This example shows how to:
1. Initialize a BatchedLLM instance
2. Generate multiple sequences in parallel
3. Process and display the results
4. Access generation statistics

Usage:
    python batched_llm_example.py

Requirements:
    - A GGUF model file (e.g., llama-2-7b-chat.Q4_K_M.gguf)
    - The llama-cpp-python package installed
"""

import os
import sys
import time
from pathlib import Path

# Add the parent directory to the Python path so we can import the BatchedLLM class
sys.path.append(str(Path(__file__).parent.parent))
from services.batched_llm import BatchedLLM


def main():
    # Configuration
    model_path = "../models/gemma-2-2b-it-Q8_0.gguf"  # Replace with your model path
    
    # Check if the model file exists
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        print("Please update the model_path variable with the correct path to your GGUF model file.")
        return
    
    # Parameters for generation
    prompt = "Once upon a time in a magical forest,"
    n_predict = 50  # Number of tokens to generate
    n_parallel = 3  # Number of parallel sequences to generate
    
    print(f"Loading model from {model_path}...")
    start_time = time.time()
    
    # Initialize the BatchedLLM
    model = BatchedLLM(
        model_or_path=model_path,
        n_ctx=2048,         # Context size
        n_threads=4,        # Number of CPU threads to use
        verbose=True        # Print verbose output
    )
    
    load_time = time.time() - start_time
    print(f"Model loaded in {load_time:.2f} seconds")
    
    print(f"\nGenerating {n_parallel} sequences in parallel with prompt: '{prompt}'")
    print(f"Each sequence will generate up to {n_predict} tokens\n")
    
    # Generate multiple sequences in parallel
    sequences, stats, logprobs = model.generate(
        prompt=prompt,
        n_predict=n_predict,
        n_parallel=n_parallel,
        top_k=40,           # Keep only the top 40 tokens
        top_p=0.95,         # Nucleus sampling threshold
        temp=0.8,           # Temperature (higher = more random)
        seed=42             # Random seed for reproducibility
    )
    
    # Display the results
    print("\n=== Generated Sequences ===")
    for i, sequence in enumerate(sequences):
        print(f"\nSequence {i+1}:")
        print(f"{sequence}")
        
        # Calculate average log probability (higher is better)
        if logprobs and i < len(logprobs) and logprobs[i]:
            avg_logprob = sum(logprobs[i]) / len(logprobs[i])
            print(f"Average token log probability: {avg_logprob:.4f}")
    
    # Display statistics
    print("\n=== Generation Statistics ===")
    print(f"Total tokens generated: {stats['n_decode']}")
    print(f"Generation time: {stats['time_s']:.2f} seconds")
    print(f"Tokens per second: {stats['tokens_per_second']:.2f}")
    
    # Clean up resources
    model.cleanup()
    print("\nResources cleaned up")


if __name__ == "__main__":
    main()
