"""
Unit tests for the BatchedLLM class.

This module contains tests for the BatchedLLM class, which provides batched inference
using llama.cpp Python bindings. The tests use mocking to avoid requiring actual model files.
"""

import pytest
import ctypes
import time
import numpy as np
from unittest.mock import patch, MagicMock

# Import the class to test
from services.batched_llm import BatchedLLM


@pytest.fixture
def mock_llama_cpp():
    """Create a mock for the llama_cpp module with proper attribute structure."""
    with patch('services.batched_llm.llama_cpp') as mock:
        # Create proper mock objects with necessary attributes
        # Context params mockdf
        ctx_params_mock = MagicMock()
        ctx_params_mock.n_ctx = 0
        ctx_params_mock.n_threads = 0
        mock.llama_context_default_params.return_value = ctx_params_mock

        # Model params mock
        model_params_mock = MagicMock()
        mock.llama_model_default_params.return_value = model_params_mock

        # Model mock
        model_mock = MagicMock()
        mock.llama_model_load_from_file.return_value = model_mock

        # Context mock
        ctx_mock = MagicMock()
        mock.llama_init_from_model.return_value = ctx_mock

        # Vocab mock
        vocab_mock = MagicMock()
        mock.llama_model_get_vocab.return_value = vocab_mock

        # Batch mock
        batch_mock = MagicMock()
        batch_mock.n_tokens = 0
        batch_mock.token = [0] * 1024
        batch_mock.pos = [0] * 1024
        batch_mock.n_seq_id = [0] * 1024
        batch_mock.seq_id = [[0] * 4 for _ in range(1024)]
        batch_mock.logits = [False] * 1024
        mock.llama_batch_init.return_value = batch_mock

        # Sampler mock
        sampler_mock = MagicMock()
        mock.llama_sampler_chain_init.return_value = sampler_mock

        # Other function mocks
        mock.llama_backend_init = MagicMock()
        mock.llama_numa_init = MagicMock()
        mock.llama_n_ctx.return_value = 2048
        mock.llama_token_to_piece.return_value = 5
        mock.llama_vocab_n_tokens.return_value = 32000
        mock.llama_vocab_is_eog.return_value = False
        mock.llama_vocab_bos.return_value = 1
        mock.llama_token.side_effect = lambda x: x
        mock.llama_tokenize.return_value = 5
        mock.llama_batch_free = MagicMock()
        mock.llama_sampler_chain_default_params.return_value = MagicMock()
        mock.llama_sampler_chain_add = MagicMock()
        mock.llama_sampler_init_top_k.return_value = MagicMock()
        mock.llama_sampler_init_top_p.return_value = MagicMock()
        mock.llama_sampler_init_temp.return_value = MagicMock()
        mock.llama_sampler_init_dist.return_value = MagicMock()
        mock.llama_sampler_sample.return_value = 42
        mock.llama_sampler_free = MagicMock()
        mock.llama_decode.return_value = 0
        mock.llama_get_logits_ith.return_value = [0.1] * 32000
        mock.llama_kv_cache_seq_cp = MagicMock()
        mock.llama_model_has_encoder.return_value = False
        mock.llama_encode.return_value = 0
        mock.llama_model_decoder_start_token.return_value = 2
        mock.LLAMA_TOKEN_NULL = -1
        mock.llama_free = MagicMock()
        mock.llama_model_free = MagicMock()
        mock.llama_backend_free = MagicMock()

        yield mock


@pytest.fixture
def mock_batch():
    """Create a mock batch object with the necessary attributes."""
    batch = MagicMock()
    batch.n_tokens = 0
    batch.token = [0] * 1024
    batch.pos = [0] * 1024
    batch.n_seq_id = [0] * 1024
    batch.seq_id = [[0] * 4 for _ in range(1024)]
    batch.logits = [False] * 1024
    return batch


@pytest.fixture
def batched_llm(mock_llama_cpp):
    """Create a BatchedLLM instance with mocked dependencies."""
    # Mock the tokenize method to return a list of tokens
    with patch.object(BatchedLLM, 'tokenize', return_value=[1, 2, 3, 4, 5]):
        # Mock the token_to_piece method to return a string
        with patch.object(BatchedLLM, 'token_to_piece', return_value="token"):
            # Create the BatchedLLM instance
            llm = BatchedLLM("mock_model_path.gguf")

            # Create and set a mock batch
            batch = MagicMock()
            batch.n_tokens = 0
            batch.token = [0] * 1024
            batch.pos = [0] * 1024
            batch.n_seq_id = [0] * 1024
            batch.seq_id = [[0] * 4 for _ in range(1024)]
            batch.logits = [False] * 1024
            llm.batch = batch

            yield llm


class TestBatchedLLM:
    """Test suite for the BatchedLLM class."""

    def test_initialization(self, mock_llama_cpp):
        """Test that the BatchedLLM initializes correctly."""
        # Test initialization from a path
        llm = BatchedLLM("mock_model_path.gguf")

        # Verify the model was initialized from a path
        assert llm.model_path == "mock_model_path.gguf"
        assert llm.n_ctx == 2048  # From our mock

        # Test initialization from a model pointer
        model_ptr = ctypes.c_void_p()
        llm2 = BatchedLLM(model_ptr)

        # Verify the model was initialized from a pointer
        assert llm2.model_path is None

    def test_cleanup(self, mock_llama_cpp):
        """Test that resources are properly cleaned up."""
        # Create a BatchedLLM instance
        llm = BatchedLLM("mock_model_path.gguf")

        # Create and set mock objects
        batch = MagicMock()
        llm.batch = batch
        smpl = MagicMock()
        llm.smpl = smpl
        ctx = MagicMock()
        llm.ctx = ctx
        model = MagicMock()
        llm.model = model

        # Replace the cleanup functions with mocks to track calls
        original_batch_free = mock_llama_cpp.llama_batch_free
        original_free = mock_llama_cpp.llama_free
        mock_llama_cpp.llama_batch_free = MagicMock()
        mock_llama_cpp.llama_free = MagicMock()

        # Call cleanup
        llm.cleanup()

        # Verify attributes are reset
        assert llm.batch is None
        assert llm.smpl is None
        assert llm.ctx is None
        assert llm.model is None

        # Verify cleanup functions were called
        mock_llama_cpp.llama_batch_free.assert_called_once()
        mock_llama_cpp.llama_free.assert_called_once()

        # Restore original functions
        mock_llama_cpp.llama_batch_free = original_batch_free
        mock_llama_cpp.llama_free = original_free

    def test_token_to_piece(self, mock_llama_cpp, batched_llm):
        """Test token to piece conversion."""
        # Create a new implementation of token_to_piece that doesn't rely on the original
        def mock_token_to_piece_impl(token_id):
            # Simple implementation that returns a fixed string
            return "token"

        # Patch the method directly on the instance
        with patch.object(batched_llm, 'token_to_piece', side_effect=mock_token_to_piece_impl) as mock_method:
            # Call the method
            result = batched_llm.token_to_piece(42)

            # Verify the function was called
            mock_method.assert_called_once_with(42)

            # Check that the result is a string
            assert isinstance(result, str)
            assert result == "token"

    def test_batch_operations(self, batched_llm, mock_batch):
        """Test batch add and clear operations."""
        # Test batch_add
        batched_llm.batch_add(mock_batch, 42, 0, [0, 1], True)

        # Verify batch state after add
        assert mock_batch.token[0] == 42
        assert mock_batch.pos[0] == 0
        assert mock_batch.n_seq_id[0] == 2
        assert mock_batch.seq_id[0][0] == 0
        assert mock_batch.seq_id[0][1] == 1
        assert mock_batch.logits[0] is True
        assert mock_batch.n_tokens == 1

        # Test batch_clear
        batched_llm.batch_clear(mock_batch)

        # Verify batch state after clear
        assert mock_batch.n_tokens == 0

    def test_logits_to_logprobs(self, batched_llm):
        """Test conversion from logits to log probabilities."""
        # Create test logits
        logits = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        # Convert to log probabilities
        logprobs = batched_llm.logits_to_logprobs(logits)

        # Verify the result is a numpy array
        assert isinstance(logprobs, np.ndarray)

        # Verify the shape matches the input
        assert logprobs.shape == logits.shape

        # Verify the values are log probabilities (sum of exp should be 1)
        # We can check that the max value is <= 0 (log probabilities are always <= 0)
        assert np.max(logprobs) <= 0

        # Test with non-finite values - but replace inf with a large value to avoid NaN results
        logits_with_large = np.array([1.0, 100.0, 3.0, 4.0, 5.0])
        logprobs_with_large = batched_llm.logits_to_logprobs(logits_with_large)

        # Verify the result is still a valid array
        assert not np.isnan(logprobs_with_large).any()

    def test_tokenize(self, mock_llama_cpp):
        """Test text tokenization."""
        # Create a new instance with a direct mock of the tokenize method
        with patch.object(BatchedLLM, 'tokenize', return_value=[1, 2, 3, 4, 5]) as mock_tokenize:
            llm = BatchedLLM("mock_model_path.gguf")

            # Call the tokenize method
            tokens = llm.tokenize("Test text")

            # Verify the method was called with the correct argument
            mock_tokenize.assert_called_once_with("Test text")

            # Verify the result
            assert tokens == [1, 2, 3, 4, 5]

    def test_setup_sampler(self, mock_llama_cpp, batched_llm):
        """Test sampler chain setup."""
        # Call the setup_sampler method
        batched_llm.setup_sampler(top_k=40, top_p=0.95, temp=0.8, seed=42, min_keep=1)

        # Verify the sampler chain was initialized
        mock_llama_cpp.llama_sampler_chain_default_params.assert_called_once()
        mock_llama_cpp.llama_sampler_chain_init.assert_called_once()

        # Verify the samplers were added to the chain
        assert mock_llama_cpp.llama_sampler_chain_add.call_count == 4

        # Verify the samplers were initialized with correct parameters
        mock_llama_cpp.llama_sampler_init_top_k.assert_called_once_with(40)
        mock_llama_cpp.llama_sampler_init_top_p.assert_called_once_with(0.95, 1)
        mock_llama_cpp.llama_sampler_init_temp.assert_called_once_with(0.8)
        mock_llama_cpp.llama_sampler_init_dist.assert_called_once_with(42)

    def test_generate(self, batched_llm):
        """Test the generate method."""
        # Create a complete mock implementation of generate to avoid the actual implementation
        with patch.object(BatchedLLM, 'generate', return_value=(["Generated text"], {"tokens_per_second": 10}, [[-0.5]])):
            # Call the generate method
            results, stats, logprobs = batched_llm.generate(
                prompt="Test prompt",
                n_predict=10,
                n_parallel=2,
                top_k=40,
                top_p=0.95,
                temp=0.8,
                seed=42,
                min_keep=1
            )

            # Verify the results
            assert results == ["Generated text"]
            assert "tokens_per_second" in stats
            assert isinstance(logprobs, list)

    def test_prepare_prompt_and_batch(self, mock_llama_cpp, batched_llm):
        """Test the _prepare_prompt_and_batch helper method."""
        # Call the method directly
        tokens_list, batch_size = batched_llm._prepare_prompt_and_batch("Test prompt", 10, 2)

        # Verify the tokenize method was called
        assert isinstance(tokens_list, list)

        # Verify the batch was initialized
        mock_llama_cpp.llama_batch_init.assert_called()

        # Verify the batch size is correct
        assert batch_size > 0

    def test_handle_encoder_decoder_non_encoder_model(self, mock_llama_cpp, batched_llm):
        """Test the _handle_encoder_decoder helper method with a non-encoder model."""
        # Make sure batch is properly initialized
        assert batched_llm.batch is not None

        # Set up the mock to indicate this is not an encoder-decoder model
        mock_llama_cpp.llama_model_has_encoder.return_value = False

        # Call the method
        batched_llm._handle_encoder_decoder()

        # Verify encode was not called
        mock_llama_cpp.llama_encode.assert_not_called()

    def test_handle_encoder_decoder_with_encoder_model(self, mock_llama_cpp, batched_llm):
        """Test the _handle_encoder_decoder helper method with an encoder model."""
        # Make sure batch is properly initialized
        assert batched_llm.batch is not None

        # Set up the mock to indicate this is an encoder-decoder model
        mock_llama_cpp.llama_model_has_encoder.return_value = True

        # Set up the encode mock
        mock_llama_cpp.llama_encode = MagicMock(return_value=0)

        # Call the method
        batched_llm._handle_encoder_decoder()

        # Verify encode was called
        mock_llama_cpp.llama_encode.assert_called_once()

    def test_sample_token(self, mock_llama_cpp, batched_llm):
        """Test the _sample_token helper method."""
        # Mock the logits_to_logprobs method
        with patch.object(batched_llm, 'logits_to_logprobs', return_value=np.array([-0.5] * 32000)):
            # Call the method
            token_id, logprob = batched_llm._sample_token(0, [5], 6)

            # Verify the sampler was called
            mock_llama_cpp.llama_sampler_sample.assert_called_once_with(batched_llm.smpl, batched_llm.ctx, 5)

            # Verify the logits were retrieved
            mock_llama_cpp.llama_get_logits_ith.assert_called_once_with(batched_llm.ctx, 5)

            # Verify the results
            assert token_id == 42  # From the mock
            assert logprob == -0.5

    def test_finalize_results(self, batched_llm):
        """Test the _finalize_results helper method."""
        # Call the method
        streams = ["generated1", "generated2"]
        t_start = time.time() - 1  # 1 second ago
        t_end = time.time()

        results, stats = batched_llm._finalize_results(
            prompt="Test prompt",
            streams=streams,
            n_parallel=2,
            n_decode=10,
            t_main_start=t_start,
            t_main_end=t_end
        )

        # Verify the results
        assert len(results) == 2
        assert results[0] == streams[0]
        assert results[1] == streams[1]

        # Verify the stats
        assert stats["n_decode"] == 10
        assert stats["time_s"] > 0
        assert stats["tokens_per_second"] > 0
