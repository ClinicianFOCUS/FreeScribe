"""
Library for batched inference using llama.cpp Python bindings.

This provides a clean API for generating multiple sequences in parallel.
The BatchedLLM class is a high-performance wrapper around the low-level llama.cpp
Python bindings that enables efficient parallel text generation with LLMs.

Key features:
- Generate multiple text sequences in parallel for improved throughput
- Direct access to low-level sampling parameters (top-k, top-p, temperature)
- Efficient memory usage through KV cache sharing
- Proper resource management for C/C++ allocated memory
- Performance statistics tracking
"""


import ctypes
import multiprocessing
import time
from typing import List, Optional, Dict, Any, Tuple, Union
import numpy as np

import llama_cpp
from utils.log_config import logger


class BatchedLLM:
    """
    A class for batched inference using llama.cpp Python bindings.

    This class provides methods for generating multiple sequences in parallel
    using the low-level API of llama.cpp. It abstracts away much of the complexity
    of the low-level API while still providing access to advanced features.

    The class manages the lifecycle of llama.cpp resources (model, context, batch, sampler)
    and provides a clean API for text generation. It's designed for high-performance
    applications where generating multiple sequences in parallel is beneficial.

    Key components:
    - Model and context management: Loads and manages the LLM model and its context
    - Batch processing: Efficiently processes tokens in batches
    - Sampling configuration: Provides control over token sampling parameters
    - Parallel generation: Generates multiple sequences simultaneously
    - Resource cleanup: Properly frees C/C++ resources

    Usage example:
        model = BatchedLLM("path/to/model.gguf")
        sequences, stats, logprobs = model.generate(
            prompt="Hello, I am",
            n_predict=50,
            n_parallel=4
        )
    """

    def __init__(
        self,
        model_or_path: Union[str, ctypes.c_void_p],
        n_ctx: Optional[int] = None,
        n_threads: Optional[int] = None,
        numa: bool = False,
        verbose: bool = False
    ):
        """
        Initialize the BatchedLLM.

        This method sets up the model, context, and other resources needed for inference.
        It can either load a model from a file path or use an already loaded model pointer,
        providing flexibility in how models are managed.

        The context size (n_ctx) is a critical parameter that determines the maximum
        number of tokens that can be processed at once. This includes both the prompt
        and the generated tokens across all parallel sequences. If not specified,
        it will be determined automatically based on the model's default settings.

        :param model_or_path: Either a path to the model file or a loaded model pointer
        :type model_or_path: Union[str, ctypes.c_void_p]
        :param n_ctx: Context size (if None, will be determined automatically)
        :type n_ctx: Optional[int]
        :param n_threads: Number of threads to use for computation
        :type n_threads: int
        :param numa: Whether to use NUMA optimization for multi-socket systems
        :type numa: bool
        :param verbose: Whether to print verbose output during processing
        :type verbose: bool
        :raises RuntimeError: If the model cannot be loaded or context cannot be created
        """
        # Store configuration parameters
        self.n_threads = n_threads
        self.numa = numa
        self.verbose = verbose
        self.model_path = None

        # Initialize the llama backend if loading from path
        # This branch handles loading a model from a file path
        if isinstance(model_or_path, str):
            self.model_path = model_or_path
            # Initialize the llama backend - this must be done before loading any models
            llama_cpp.llama_backend_init()
            # Initialize NUMA if requested - important for multi-socket systems
            llama_cpp.llama_numa_init(numa)

            # Initialize the model with default parameters
            # This creates a model configuration with sensible defaults
            model_params = llama_cpp.llama_model_default_params()

            # Load the model from file - this is a potentially expensive operation
            # that reads the model weights from disk and initializes the model
            self.model = llama_cpp.llama_model_load_from_file(model_or_path.encode("utf-8"), model_params)

            # Check if model loading was successful
            if self.model is None:
                raise RuntimeError(f"Unable to load model from {model_or_path}")
        else:
            # Use the provided model pointer - this allows reusing an already loaded model
            # which can be useful in scenarios where multiple BatchedLLM instances
            # need to share the same model
            self.model = model_or_path

        # Get the vocabulary associated with the model
        # This is needed for tokenization and token-to-text conversion
        self.vocab = llama_cpp.llama_model_get_vocab(self.model)

        # Initialize the context with default parameters
        # The context is where the actual computation happens and where
        # the KV cache is stored
        self.ctx_params = llama_cpp.llama_context_default_params()

        # Set context size if provided
        # The context size determines how many tokens can be processed at once
        if n_ctx is not None:
            self.ctx_params.n_ctx = n_ctx

        # Set number of threads for parallel computation
        self.ctx_params.n_threads = n_threads or multiprocessing.cpu_count()

        # Commented out line below shows an alternative parameter that might be used
        # in future versions of llama.cpp
        # self.ctx_params.n_ctx_per_seq = n_ctx

        # Ensure n_ctx is set (redundant with line above but kept for clarity)
        self.ctx_params.n_ctx = n_ctx

        # Create the context from the model and parameters
        # This allocates memory for the KV cache and other resources
        self.ctx = llama_cpp.llama_init_from_model(self.model, self.ctx_params)

        # Check if context creation was successful
        # If not, clean up resources to prevent memory leaks
        if self.ctx is None:
            llama_cpp.llama_model_free(self.model)
            llama_cpp.llama_backend_free()
            raise RuntimeError("Failed to create the llama_context")

        # Get the actual context size that was allocated
        # This might be different from what was requested if the model
        # has specific requirements or if n_ctx was None
        self.n_ctx = llama_cpp.llama_n_ctx(self.ctx)
        logger.debug(f"{self.n_ctx=}")  # Print for debugging/information

        # Initialize other attributes that will be set up later
        # These will be created during the generate method
        self.batch = None  # Will hold the batch of tokens for processing
        self.smpl = None   # Will hold the sampler chain for token generation

    def __del__(self):
        """Clean up resources when the object is deleted.

        This method is automatically called when the object is garbage collected.
        """
        # Use a flag to prevent recursive calls between __del__ and cleanup
        if not hasattr(self, '_is_cleaning_up') or not self._is_cleaning_up:
            self._is_cleaning_up = True
            self.cleanup()

    def cleanup(self):
        """Clean up resources.

        Frees all allocated resources including batch, sampler, context, and model.
        This method is crucial for preventing memory leaks when working with C/C++ resources.
        It follows a specific order of cleanup to ensure proper resource management.

        The method is automatically called by __del__ when the object is garbage collected,
        but can also be called manually if early cleanup is desired.
        """
        # Check if we're already in the process of cleaning up to prevent recursion
        if hasattr(self, '_is_cleaning_up') and self._is_cleaning_up:
            return

        # Set the flag to indicate we're cleaning up
        self._is_cleaning_up = True
        # Free the batch if it exists
        # The batch contains token data for processing and must be freed to prevent memory leaks
        if hasattr(self, 'batch') and self.batch is not None:
            llama_cpp.llama_batch_free(self.batch)
            self.batch = None

        # Free the sampler chain if it exists
        # The sampler chain contains the sampling methods used for token generation
        if hasattr(self, 'smpl') and self.smpl is not None:
            llama_cpp.llama_sampler_free(self.smpl)
            self.smpl = None

        # Free the context if it exists
        # The context contains the KV cache and other computational resources
        if hasattr(self, 'ctx') and self.ctx is not None:
            llama_cpp.llama_free(self.ctx)
            self.ctx = None

        # Only free the model if we loaded it ourselves (i.e., from a path)
        # This allows for model sharing between multiple BatchedLLM instances
        if hasattr(self, 'model') and self.model is not None and self.model_path is not None:
            llama_cpp.llama_model_free(self.model)
            self.model = None

            # Only free the backend if we initialized it
            # The backend is a global resource that should only be freed once
            llama_cpp.llama_backend_free()

    def token_to_piece(self, token_id: int) -> str:
        """
        Convert a token ID to its string representation (piece).

        This method translates a numeric token ID back into its corresponding text piece.
        Note that pieces are not necessarily complete words or characters - they are the
        basic units used by the tokenizer, which can be subwords, characters, or even
        byte sequences depending on the tokenization algorithm.

        The method allocates a buffer to receive the piece text and handles proper
        UTF-8 decoding with error replacement for any invalid sequences.

        :param token_id: The token ID to convert
        :type token_id: int
        :return: The string representation of the token
        :rtype: str
        """
        # Allocate a buffer to receive the piece text
        # 32 bytes is usually enough for most tokens, but this could be increased
        # for languages with multi-byte characters if needed
        buf_size = 32
        buf = (ctypes.c_char * buf_size)()

        # Call the llama.cpp function to convert the token to a piece
        n = llama_cpp.llama_token_to_piece(
            self.vocab,            # The vocabulary to use
            llama_cpp.llama_token(token_id),  # Convert to llama_token type
            buf,                  # Output buffer
            buf_size,             # Size of the buffer
            0,                    # Offset in the buffer
            True                  # Allow special tokens (like BOS, EOS, etc.)
        )

        # Ensure the buffer was large enough
        assert n <= buf_size, "Buffer overflow in token_to_piece"

        # Decode the bytes to a UTF-8 string, replacing any invalid sequences
        return buf[:n].decode("utf-8", errors="replace")

    def batch_add(self, batch, token_id: int, pos: int, seq_ids: List[int], compute_logits: bool = False):
        """
        Add a token to the batch for processing.

        This method adds a token to the batch with its associated metadata. The batch
        is a data structure that holds tokens to be processed together by the model.

        Batching tokens together is more efficient than processing them one by one,
        as it allows for better parallelization on the GPU or CPU.

        The sequence IDs allow for tracking multiple sequences within a single batch,
        which is essential for parallel generation.

        :param batch: The batch to add the token to
        :param token_id: The token ID to add
        :type token_id: int
        :param pos: The position of the token in its sequence
        :type pos: int
        :param seq_ids: The sequence IDs to associate with the token (which sequences this token belongs to)
        :type seq_ids: List[int]
        :param compute_logits: Whether to compute logits for this token (needed for sampling)
        :type compute_logits: bool
        """
        # Get the current index in the batch
        i = batch.n_tokens

        # Set the token ID at the current index
        batch.token[i] = token_id

        # Set the position of the token in its sequence
        batch.pos[i] = pos

        # Set the number of sequences this token belongs to
        batch.n_seq_id[i] = len(seq_ids)

        # Set the sequence IDs for this token
        # A token can belong to multiple sequences in some cases
        for j, seq_id in enumerate(seq_ids):
            batch.seq_id[i][j] = seq_id

        # Set whether to compute logits for this token
        # Only needed for tokens that will be used for sampling
        batch.logits[i] = compute_logits

        # Increment the token count in the batch
        batch.n_tokens += 1

    def batch_clear(self, batch):
        """
        Clear the batch by resetting its token count.

        This method resets the batch to an empty state, allowing it to be reused
        for the next round of token processing. This is more efficient than
        creating a new batch for each round.

        Note that this doesn't deallocate any memory - it just marks the batch
        as empty so that new tokens can be added starting from index 0.

        :param batch: The batch to clear
        """
        # Reset the token count to 0, effectively clearing the batch
        batch.n_tokens = 0

    def logits_to_logprobs(self, logits, axis=-1):
        """
        Convert logits (raw model outputs) to log probabilities.

        This method implements a numerically stable way to convert the raw logits
        from the model to log probabilities, which are needed for token sampling.

        The conversion follows these steps:
        1. Subtract the maximum logit value for numerical stability
        2. Apply the exponential function to get unnormalized probabilities
        3. Sum the unnormalized probabilities
        4. Take the log of the sum
        5. Subtract the log sum from the shifted logits to get log probabilities

        This approach avoids numerical overflow/underflow issues that can occur
        when working with very large or very small logit values.

        :param logits: The logits to convert (raw model outputs)
        :type logits: numpy.ndarray
        :param axis: The axis along which to compute softmax (usually the vocabulary axis)
        :type axis: int
        :return: Log probabilities for each token in the vocabulary
        :rtype: numpy.ndarray
        """
        # Implementation based on llama_cpp.Llama.logits_to_logprobs

        # Step 1: Find the maximum logit value for numerical stability
        # This prevents overflow when applying exp() to large values
        logits_maxs = np.amax(logits, axis=axis, keepdims=True)

        # Handle non-finite values (NaN, inf) by replacing them with 0
        if logits_maxs.ndim > 0:
            logits_maxs[~np.isfinite(logits_maxs)] = 0
        elif not np.isfinite(logits_maxs):
            logits_maxs = 0

        # Step 2: Subtract the maximum from all logits
        # This shifts the logits to be <= 0, preventing overflow
        subtract_maxs = np.subtract(logits, logits_maxs, dtype=np.float32)

        # Step 3: Apply exp() to get unnormalized probabilities
        exp = np.exp(subtract_maxs)

        # Step 4: Sum the unnormalized probabilities and take log
        # Suppress warnings about log of zero which can occur with very small probabilities
        with np.errstate(divide="ignore"):
            summed = np.sum(exp, axis=axis, keepdims=True)
            out = np.log(summed)

        # Step 5: Subtract the log sum to get log probabilities
        # This is equivalent to log(exp(logits - max) / sum(exp(logits - max)))
        return subtract_maxs - out

    def tokenize(self, text: str) -> List[int]:
        """
        Tokenize a text string into token IDs.

        This method converts a text string into a sequence of token IDs that the model
        can process. Tokenization is the process of breaking down text into smaller units
        (tokens) according to the model's vocabulary.

        The method allocates a buffer to receive the tokens, calls the llama.cpp tokenization
        function, and then converts the result to a Python list of token IDs.

        Note that the tokenization includes adding a BOS (Beginning of Sequence) token
        by default, which is important for proper model conditioning.

        :param text: The text to tokenize
        :type text: str
        :return: A list of token IDs representing the tokenized text
        :rtype: List[int]
        :raises RuntimeError: If tokenization fails (e.g., if the buffer is too small)
        """
        # Convert the text to UTF-8 bytes for the C API
        text_bytes = text.encode("utf-8")

        # Allocate a buffer for the tokens with a refined heuristic to reduce buffer overflow risks
        MAX_TOKEN_BUF_SIZE = 10000  # Maximum allowed token buffer size
        # Calculate token buffer size: twice the input text length, capped by MAX_TOKEN_BUF_SIZE
        tokens_buf_size = min(len(text_bytes) * 2, MAX_TOKEN_BUF_SIZE)
        tokens_buf = (llama_cpp.llama_token * tokens_buf_size)()

        # Call the llama.cpp tokenization function
        n_tokens = llama_cpp.llama_tokenize(
            self.vocab,           # The vocabulary to use
            text_bytes,           # The input text as UTF-8 bytes
            len(text_bytes),      # The length of the input text
            tokens_buf,           # The output buffer for tokens
            tokens_buf_size,      # The size of the output buffer
            True,                 # Add BOS (Beginning of Sequence) token
            True,                 # Allow special tokens in the output
        )

        # Check if tokenization was successful
        if n_tokens <= 0:
            raise RuntimeError("Failed to tokenize the text")

        # Convert the C array to a Python list
        return [tokens_buf[i] for i in range(n_tokens)]

    def setup_sampler(
        self,
        top_k: int = 40,
        top_p: float = 0.95,
        temp: float = 0.1,
        seed: int = 1337,
        min_keep: int = 1
    ):
        """
        Set up a sampler chain with various sampling methods for token generation.

        This method creates a chain of samplers that will be used to sample the next token
        during generation. The samplers are applied in sequence, each filtering the token
        distribution according to its specific algorithm.

        The sampler chain includes:
        1. Top-K sampling: Keeps only the top K most likely tokens
        2. Top-P (nucleus) sampling: Keeps the smallest set of tokens whose cumulative probability exceeds P
        3. Temperature sampling: Adjusts the "sharpness" of the distribution
        4. Distribution sampling: Samples from the final distribution using the provided random seed

        These sampling methods work together to produce more diverse and interesting
        text while still maintaining coherence and relevance.

        :param top_k: Top-k sampling parameter (keep only the top k most likely tokens)
        :type top_k: int
        :param top_p: Top-p sampling parameter (keep smallest set of tokens with cumulative probability > p)
        :type top_p: float
        :param temp: Temperature parameter (higher = more random, lower = more deterministic)
        :type temp: float
        :param seed: Random seed for reproducibility
        :type seed: int
        :param min_keep: Minimum number of tokens to keep regardless of top-p filtering
        :type min_keep: int
        :return: The initialized sampler chain
        :rtype: ctypes.c_void_p
        """
        # Initialize sampler chain parameters
        sparams = llama_cpp.llama_sampler_chain_default_params()
        # Only show performance metrics if verbose mode is enabled
        sparams.no_perf = not self.verbose

        # Initialize the sampler chain with the parameters
        self.smpl = llama_cpp.llama_sampler_chain_init(sparams)

        # Add samplers to the chain in a specific order
        # The order matters as each sampler filters the distribution produced by the previous one

        # 1. Top-K sampling: Keep only the top K most likely tokens
        # This reduces the vocabulary to consider for subsequent sampling steps
        llama_cpp.llama_sampler_chain_add(self.smpl, llama_cpp.llama_sampler_init_top_k(top_k))

        # 2. Top-P (nucleus) sampling: Keep smallest set of tokens with cumulative probability > p
        # This dynamically adjusts the number of tokens based on their probability distribution
        llama_cpp.llama_sampler_chain_add(self.smpl, llama_cpp.llama_sampler_init_top_p(top_p, min_keep))

        # 3. Temperature sampling: Adjust the "sharpness" of the distribution
        # Lower temperature makes high-probability tokens more likely, higher makes distribution more uniform
        llama_cpp.llama_sampler_chain_add(self.smpl, llama_cpp.llama_sampler_init_temp(temp))

        # 4. Distribution sampling: Sample from the final distribution using the provided random seed
        # This is the final step that actually selects a token based on the filtered and adjusted distribution
        llama_cpp.llama_sampler_chain_add(self.smpl, llama_cpp.llama_sampler_init_dist(seed))

        return self.smpl

    def _prepare_prompt_and_batch(self, prompt: str, n_predict: int, n_parallel: int) -> Tuple[List[int], int]:
        """
        Prepare the prompt by tokenizing it and initializing the batch.

        This helper method handles the initial setup for generation:
        1. Tokenizes the prompt
        2. Checks if the required KV cache size fits in the context
        3. Creates and initializes the batch with prompt tokens

        :param prompt: The prompt to start generation with
        :type prompt: str
        :param n_predict: Maximum number of tokens to predict
        :type n_predict: int
        :param n_parallel: Number of parallel sequences to generate
        :type n_parallel: int
        :return: A tuple containing the tokenized prompt and batch size
        :rtype: Tuple[List[int], int]
        :raises RuntimeError: If the required KV cache size exceeds context size
        """
        # Tokenize the prompt
        tokens_list = self.tokenize(prompt)

        # Calculate required KV cache size
        n_kv_req = len(tokens_list) + (n_predict - len(tokens_list)) * n_parallel

        # Check if the required KV cache size fits in the context
        if n_kv_req > self.n_ctx:
            raise RuntimeError(
                f"Required KV cache size ({n_kv_req}) exceeds context size ({self.n_ctx}). "
                "Either reduce n_parallel or increase n_ctx."
            )

        # Create a batch for token processing
        batch_size = max(len(tokens_list), n_parallel)
        self.batch = llama_cpp.llama_batch_init(batch_size, 0, n_parallel)

        # Add the prompt tokens to the batch
        for i, token_id in enumerate(tokens_list):
            self.batch_add(self.batch, token_id, i, [0], False)

        return tokens_list, batch_size

    def _handle_encoder_decoder(self):
        """
        Handle special processing for encoder-decoder models.

        This helper method processes encoder-decoder models differently:
        1. Encodes the prompt tokens
        2. Clears the batch
        3. Adds the decoder start token

        :raises RuntimeError: If encoding fails
        """
        if not llama_cpp.llama_model_has_encoder(self.model):
            return

        # Encode the prompt tokens
        if llama_cpp.llama_encode(self.ctx, self.batch) != 0:
            raise RuntimeError("Failed to encode")

        # Get the decoder start token
        decoder_start_token_id = llama_cpp.llama_model_decoder_start_token(self.model)
        if decoder_start_token_id == llama_cpp.LLAMA_TOKEN_NULL:
            decoder_start_token_id = llama_cpp.llama_vocab_bos(self.vocab)

        # Clear the batch and add the decoder start token
        self.batch_clear(self.batch)
        self.batch_add(self.batch, decoder_start_token_id, 0, [0], False)

    def _sample_token(self, seq_index: int, i_batch: List[int], n_cur: int) -> Tuple[int, float]:
        """
        Sample the next token for a given sequence.

        This helper method handles the token sampling process:
        1. Samples a new token using the sampler chain
        2. Calculates log probabilities for the token

        :param seq_index: The index of the sequence to sample for
        :type seq_index: int
        :param i_batch: List of batch indices for each sequence
        :type i_batch: List[int]
        :param n_cur: Current position in the sequence
        :type n_cur: int
        :return: A tuple containing the new token ID and its log probability
        :rtype: Tuple[int, float]
        """
        # Sample the next token for this sequence
        new_token_id = llama_cpp.llama_sampler_sample(self.smpl, self.ctx, i_batch[seq_index])

        # Get the logits for the current token
        logits = llama_cpp.llama_get_logits_ith(self.ctx, i_batch[seq_index])
        n_vocab = llama_cpp.llama_vocab_n_tokens(self.vocab)

        # Convert the logits to a numpy array for easier processing
        logits_array = np.array(
            [logits[j] for j in range(n_vocab)],
            dtype=np.float32
        )

        # Convert logits to log probabilities
        logprobs_array = self.logits_to_logprobs(logits_array)

        # Return the token and its log probability
        return new_token_id, logprobs_array[new_token_id]

    def _finalize_results(self, prompt: str, streams: List[str], n_parallel: int,
                          n_decode: int, t_main_start: float, t_main_end: float) -> Tuple[List[str], Dict[str, Any]]:
        """
        Finalize the generation results and prepare statistics.

        This helper method handles the final processing of results:
        1. Returns only the newly generated text for each sequence (without the prompt)
        2. Calculates and prepares statistics
        3. Cleans up resources

        :param prompt: The original prompt
        :type prompt: str
        :param streams: List of generated text for each sequence
        :type streams: List[str]
        :param n_parallel: Number of parallel sequences
        :type n_parallel: int
        :param n_decode: Number of tokens decoded
        :type n_decode: int
        :param t_main_start: Start time of generation
        :type t_main_start: float
        :param t_main_end: End time of generation
        :type t_main_end: float
        :return: A tuple containing the results and statistics
        :rtype: Tuple[List[str], Dict[str, Any]]
        """
        # Return the prompt + generated text for each sequence
        results = [streams[i] for i in range(n_parallel)]

        # Calculate and prepare statistics
        stats = {
            "n_decode": n_decode,  # Total number of tokens decoded
            "time_s": t_main_end - t_main_start,  # Total time in seconds
            "tokens_per_second": n_decode / (t_main_end - t_main_start) if t_main_end > t_main_start else 0,  # Throughput
        }

        # Clean up resources
        llama_cpp.llama_batch_free(self.batch)
        self.batch = None

        llama_cpp.llama_sampler_free(self.smpl)
        self.smpl = None

        return results, stats

    def generate(
        self,
        prompt: str,
        n_predict: int = 32,
        n_parallel: int = 4,
        top_k: int = 40,
        top_p: float = 0.95,
        temp: float = 0.8,
        seed: int = 42,
        min_keep: int = 1
    ) -> Tuple[List[str], Dict[str, Any], Optional[List[List[float]]]]:
        """
        Generate multiple sequences in parallel from a single prompt.

        This is the main method of the BatchedLLM class, which handles the entire
        generation process from tokenizing the prompt to returning the generated sequences.

        The method generates n_parallel different sequences starting from the same prompt,
        which can be useful for exploring different possible continuations or for
        selecting the best continuation based on some criteria.

        The generation process follows these steps:
        1. Tokenize the prompt
        2. Check if the required KV cache size fits in the context
        3. Set up the sampler chain for token generation
        4. Process the prompt tokens
        5. Copy the KV cache to all parallel sequences
        6. Generate tokens in parallel until completion
        7. Collect results and statistics

        The method returns three items:
        - A list of generated sequences (including the prompt + generated text)
        - Statistics about the generation process
        - Log probabilities for each generated token

        :param prompt: The prompt to start generation with
        :type prompt: str
        :param n_predict: Maximum number of tokens to predict (including prompt tokens)
        :type n_predict: int
        :param n_parallel: Number of parallel sequences to generate
        :type n_parallel: int
        :param top_k: Top-k sampling parameter (keep only the top k most likely tokens)
        :type top_k: int
        :param top_p: Top-p sampling parameter (keep smallest set of tokens with cumulative probability > p)
        :type top_p: float
        :param temp: Temperature parameter (higher = more random, lower = more deterministic)
        :type temp: float
        :param seed: Random seed for reproducibility
        :type seed: int
        :param min_keep: Minimum number of tokens to keep regardless of top-p filtering
        :type min_keep: int
        :return: A tuple containing (generated_sequences, statistics, token_logprobs)
        :rtype: Tuple[List[str], Dict[str, Any], Optional[List[List[float]]]]
        :raises RuntimeError: If generation fails due to context size or other issues
        """
        # Step 1: Prepare the prompt and batch
        tokens_list, _ = self._prepare_prompt_and_batch(prompt, n_predict, n_parallel)

        # Step 2: Set up the sampler chain for token generation
        self.setup_sampler(top_k, top_p, temp, seed, min_keep)

        # Step 3: Handle encoder-decoder models (if applicable)
        self._handle_encoder_decoder()

        # Compute logits for the last token of the prompt
        self.batch.logits[self.batch.n_tokens - 1] = True

        # Process the batch (forward pass through the model)
        if llama_cpp.llama_decode(self.ctx, self.batch) != 0:
            raise RuntimeError("llama_decode() failed")

        # Step 4: Copy the KV cache to all parallel sequences
        for i in range(1, n_parallel):
            llama_cpp.llama_kv_cache_seq_cp(self.ctx, 0, i, -1, -1)

        # Step 5: Main generation loop

        # Initialize storage for generated text and token log probabilities
        streams = [""] * n_parallel  # Text generated for each sequence
        token_logprobs = [[] for _ in range(n_parallel)]  # Log probs for each token in each sequence

        # Track the batch index of the last token for each sequence
        i_batch = [self.batch.n_tokens - 1] * n_parallel

        # Initialize counters for the current position and number of decoded tokens
        n_cur = self.batch.n_tokens  # Current position in the sequence
        n_decode = 0  # Number of tokens decoded (for statistics)

        # Start timing for performance measurement
        t_main_start = time.time()

        # Main generation loop
        while n_cur <= n_predict:
            # Clear the batch for the next round of tokens
            self.batch_clear(self.batch)

            # Process each parallel sequence
            for i in range(n_parallel):
                # Skip sequences that have already finished
                if i_batch[i] < 0:
                    continue

                # Debug output
                logger.debug(f"Sampling token {n_cur} for sequence {i}")

                # Sample the next token and get its log probability
                new_token_id, token_logprob = self._sample_token(i, i_batch, n_cur)
                token_logprobs[i].append(token_logprob)

                # Check if we should end generation for this sequence
                if llama_cpp.llama_vocab_is_eog(self.vocab, new_token_id) or n_cur == n_predict:
                    # Mark this sequence as finished
                    i_batch[i] = -1
                    continue

                # Add the generated token to the sequence's output stream
                streams[i] += self.token_to_piece(new_token_id)

                # Update the batch index for this sequence
                i_batch[i] = self.batch.n_tokens

                # Add the token to the batch for processing
                self.batch_add(self.batch, new_token_id, n_cur, [i], True)

                # Increment the decode counter for statistics
                n_decode += 1

            # Check if all sequences are finished
            if self.batch.n_tokens == 0:
                break

            # Move to the next position
            n_cur += 1

            # Process the batch (forward pass through the model)
            if llama_cpp.llama_decode(self.ctx, self.batch) != 0:
                raise RuntimeError("Failed to decode")

        # End timing for performance measurement
        t_main_end = time.time()

        # Step 6: Finalize results and prepare statistics
        results, stats = self._finalize_results(
            prompt, streams, n_parallel, n_decode, t_main_start, t_main_end
        )

        # Return the generated sequences, statistics, and token log probabilities
        return results, stats, token_logprobs
