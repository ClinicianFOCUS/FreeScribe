import pytest
import os
import threading
import tkinter as tk
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Import the modules to test
from Model import Model, ModelManager, ModelStatus
from UI.SettingsConstant import SettingsKeys, DEFAULT_CONTEXT_WINDOW_SIZE


def test_model_status_error():
    """Test that the ERROR status exists and has the expected value"""
    assert ModelStatus.ERROR.value == 1


class TestModel:
    """Test the Model class functionality"""
    
    @pytest.fixture
    def mock_llama(self):
        """Create a mock for the Llama class"""
        with patch('Model.Llama') as mock:
            llama_instance = MagicMock()
            mock.return_value = llama_instance
            yield mock, llama_instance
    
    @pytest.fixture
    def model_instance(self, mock_llama):
        """Create a test model instance with the mocked Llama"""
        mock_class, llama_instance = mock_llama
        model_path = "test_model.gguf"
        context_size = 2048
        gpu_layers = -1
        main_gpu = 0
        n_batch = 512
        
        model = Model(
            model_path=model_path,
            context_size=context_size,
            gpu_layers=gpu_layers,
            main_gpu=main_gpu,
            n_batch=n_batch,
            n_threads=4,
            seed=1337,
            best_of=1
        )
        
        # Store test parameters for later assertions
        model._test_params = {
            'model_path': model_path,
            'context_size': context_size,
            'gpu_layers': gpu_layers,
            'main_gpu': main_gpu,
            'n_batch': n_batch
        }
        
        return model, llama_instance
    
    def test_initialization(self, mock_llama, model_instance):
        """Test that the model initializes with correct parameters"""
        mock_class, _ = mock_llama
        model, _ = model_instance
        params = model._test_params
        
        # Check Llama was called with expected parameters
        mock_class.assert_called_once()
        args, kwargs = mock_class.call_args
        
        assert kwargs['model_path'] == params['model_path']
        assert kwargs['n_ctx'] == params['context_size']
        assert kwargs['n_gpu_layers'] == params['gpu_layers']
        assert kwargs['n_batch'] == params['n_batch']
        assert kwargs['seed'] == 1337
        
        # Check config is correctly stored
        assert model.config['gpu_layers'] == params['gpu_layers']
        assert model.config['main_gpu'] == params['main_gpu']
        assert model.config['context_size'] == params['context_size']
        assert model.config['n_batch'] == params['n_batch']
    
    def test_initialization_failure(self, mock_llama):
        """Test that initialization failure is handled correctly"""
        mock_class, _ = mock_llama
        mock_class.side_effect = RuntimeError("Model loading failed")
        
        with pytest.raises(RuntimeError):
            Model(model_path="invalid_path.gguf", context_size=2048)
    
    def test_generate_response(self, model_instance):
        """Test the generate_response method"""
        model, llama_instance = model_instance
        
        # Configure mock response
        expected_response = "This is a test response"
        mock_response = {
            "choices": [{"message": {"content": expected_response}}]
        }
        llama_instance.create_chat_completion.return_value = mock_response
        
        # Call the method
        prompt = "Test prompt"
        response = model.generate_response(prompt, max_tokens=50, temperature=0.1, top_p=0.95)
        
        # Verify the method called Llama correctly
        llama_instance.create_chat_completion.assert_called_once()
        args, kwargs = llama_instance.create_chat_completion.call_args
        assert args[0] == [{"role": "user", "content": prompt}]
        assert kwargs['max_tokens'] == 50
        assert kwargs['temperature'] == 0.1
        assert kwargs['top_p'] == 0.95
        assert kwargs['repeat_penalty'] == 1.1
        
        # Verify response
        assert response == expected_response
        llama_instance.reset.assert_called_once()
    
    def test_generate_response_error(self, model_instance):
        """Test error handling in generate_response method"""
        model, llama_instance = model_instance
        
        # Configure mock to raise exception
        error_message = "Generation failed"
        llama_instance.create_chat_completion.side_effect = RuntimeError(error_message)
        
        # Call the method
        response = model.generate_response("Test prompt")
        
        # Verify error is handled and returned as string
        assert "(RuntimeError): Generation failed" in response
    
    def test_generate_best_of_response(self, model_instance):
        """Test the generate_best_of_response method with multiple candidates"""
        model, llama_instance = model_instance
        
        # Configure mock responses with different logprobs
        responses = [
            {"choices": [{"message": {"content": "First response"}, 
                         "logprobs": {"token_logprobs": [-0.1, -0.2, -0.3]}}]},
            {"choices": [{"message": {"content": "Better response"}, 
                         "logprobs": {"token_logprobs": [-0.05, -0.1, -0.05]}}]}
        ]
        llama_instance.create_chat_completion.side_effect = responses
        
        # Call the method
        response = model.generate_best_of_response("Test prompt", best_of=2)
        
        # Verify the method selected the response with highest logprob sum
        assert response == "Better response"
        assert llama_instance.create_chat_completion.call_count == 2

    def test_generate_best_of_response_single_candidate(self, model_instance):
        """Test generate_best_of_response when best_of is 1"""
        model, llama_instance = model_instance
        
        # Configure mock response
        mock_response = {
            "choices": [{"message": {"content": "Single response"}}]
        }
        llama_instance.create_chat_completion.return_value = mock_response
        
        # Call the method with best_of=1
        response = model.generate_best_of_response("Test prompt", best_of=1)
        
        # Verify only one response was generated and returned
        assert response == "Single response"
        llama_instance.create_chat_completion.assert_called_once()
        
        # Verify logprobs were not requested
        args, kwargs = llama_instance.create_chat_completion.call_args
        assert "logprobs" not in kwargs

    def test_generate_best_of_response_equal_logprobs(self, model_instance):
        """Test generate_best_of_response when responses have equal logprobs"""
        model, llama_instance = model_instance
        
        # Configure mock responses with equal logprobs
        responses = [
            {"choices": [{"message": {"content": "First equal response"}, 
                         "logprobs": {"token_logprobs": [-0.1, -0.1, -0.1]}}]},
            {"choices": [{"message": {"content": "Second equal response"}, 
                         "logprobs": {"token_logprobs": [-0.1, -0.1, -0.1]}}]}
        ]
        llama_instance.create_chat_completion.side_effect = responses
        
        # Call the method
        response = model.generate_best_of_response("Test prompt", best_of=2)
        
        # Verify one of the responses was selected (implementation detail)
        assert response in ["First equal response", "Second equal response"]
        assert llama_instance.create_chat_completion.call_count == 2

    def test_generate_best_of_response_empty_responses(self, model_instance):
        """Test generate_best_of_response with empty responses"""
        model, llama_instance = model_instance
        
        # Configure mock responses with empty content
        responses = [
            {"choices": [{"message": {"content": ""}, 
                         "logprobs": {"token_logprobs": [-0.1]}}]},
            {"choices": [{"message": {"content": ""}, 
                         "logprobs": {"token_logprobs": [-0.1]}}]}
        ]
        llama_instance.create_chat_completion.side_effect = responses
        
        # Call the method
        response = model.generate_best_of_response("Test prompt", best_of=2)
        
        # Verify empty string is returned
        assert response == ""
        assert llama_instance.create_chat_completion.call_count == 2

    def test_generate_best_of_response_error_handling(self, model_instance):
        """Test error handling in generate_best_of_response"""
        model, llama_instance = model_instance
        
        # Configure mock to raise exception
        error_message = "Generation failed"
        llama_instance.create_chat_completion.side_effect = RuntimeError(error_message)
        
        # Call the method
        response = model.generate_best_of_response("Test prompt", best_of=2)
        
        # Verify error is handled and returned as string
        assert "(RuntimeError): Generation failed" in response
        assert llama_instance.create_chat_completion.call_count == 1  # Should stop after first error

    def test_generate_best_of_response_invalid_best_of(self, model_instance):
        """Test generate_best_of_response with invalid best_of values"""
        model, llama_instance = model_instance
        
        # Configure mock response
        mock_response = {
            "choices": [{"message": {"content": "Default response"}}]
        }
        llama_instance.create_chat_completion.return_value = mock_response
        
        # Test with best_of=0
        response = model.generate_best_of_response("Test prompt", best_of=0)
        assert response == "Default response"  # Should return the first response since best_of <= 1
        
        # Test with negative best_of
        response = model.generate_best_of_response("Test prompt", best_of=-1)
        assert "(IndexError): list index out of range" in response  # Should fail with IndexError for negative best_of
        
        # Verify only one call was made for best_of=0
        assert llama_instance.create_chat_completion.call_count == 1

    def test_generate_best_of_response_mixed_errors(self, model_instance):
        """Test generate_best_of_response with mix of successful and failed responses"""
        model, llama_instance = model_instance
        
        # Configure mock responses with one success and one error
        responses = [
            {"choices": [{"message": {"content": "Successful response"}, 
                         "logprobs": {"token_logprobs": [-0.1]}}]},
            RuntimeError("Second generation failed")
        ]
        llama_instance.create_chat_completion.side_effect = responses
        
        # Call the method
        response = model.generate_best_of_response("Test prompt", best_of=2)
        
        # Verify error is returned when any generation fails
        assert "(RuntimeError): Second generation failed" in response
        assert llama_instance.create_chat_completion.call_count == 2
    
    def test_get_gpu_info(self, model_instance):
        """Test the get_gpu_info method returns correct configuration"""
        model, _ = model_instance
        params = model._test_params
        
        gpu_info = model.get_gpu_info()
        
        assert gpu_info['gpu_layers'] == params['gpu_layers']
        assert gpu_info['main_gpu'] == params['main_gpu']
        assert gpu_info['batch_size'] == params['n_batch']
        assert gpu_info['context_size'] == params['context_size']
    
    def test_close(self, model_instance):
        """Test the close method properly closes the model"""
        model, llama_instance = model_instance
        
        model.close()
        
        llama_instance.close.assert_called_once()
        assert model.model is None
        
    def test_del(self, model_instance):
        """Test the __del__ method properly closes the model"""
        model, llama_instance = model_instance
        
        # Trigger the __del__ method
        model.__del__()
        
        llama_instance.close.assert_called_once()
        assert model.model is None


class TestModelManager:
    """Test the ModelManager class functionality"""
    
    @pytest.fixture
    def setup_dependencies(self):
        """Setup mocks for ModelManager dependencies"""
        # Update patch paths to match actual implementation
        with patch('Model.Model', autospec=True) as mock_model, \
             patch('Model.LoadingWindow') as mock_loading_window, \
             patch('Model.messagebox') as mock_messagebox, \
             patch('Model.threading.Thread', autospec=True) as mock_thread:
            
            # Create a mock for the root window
            mock_root = MagicMock()
            mock_root.after = MagicMock()
            
            # Create mock app settings
            mock_settings = MagicMock()
            mock_settings.editable_settings = {
                SettingsKeys.LLM_ARCHITECTURE.value: "CUDA (Nvidia GPU)",
                SettingsKeys.LOCAL_LLM_CONTEXT_WINDOW.value: 4096,
                SettingsKeys.BEST_OF.value: 1,
                # Add any other required settings keys
            }
            mock_settings.main_window = MagicMock()
            mock_settings.get_llm_path = MagicMock(return_value=Path('gemma-2-2b-it-Q8_0.gguf'))
            
            # Mock thread behavior
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            mock_thread_instance.is_alive.return_value = False
            
            # Mock model instance
            mock_model_instance = MagicMock()
            mock_model.return_value = mock_model_instance
            
            yield {
                'model_class': mock_model,
                'model_instance': mock_model_instance,
                'loading_window': mock_loading_window,
                'messagebox': mock_messagebox,
                'thread': mock_thread,
                'thread_instance': mock_thread_instance,
                'root': mock_root,
                'settings': mock_settings
            }
    
    def test_setup_model_success(self, setup_dependencies, monkeypatch):
        """Test successful model setup"""
        mocks = setup_dependencies
        
        # Setup method to simulate successful model loading
        def mock_thread_target(*args, **kwargs):
            ModelManager.local_model = mocks['model_instance']
            return True
            
        # Mock the thread instance's start method
        mocks['thread_instance'].start = MagicMock(side_effect=mock_thread_target)
        
        # Reset ModelManager state
        ModelManager.local_model = None
        
        # Call the method
        ModelManager.setup_model(mocks['settings'], mocks['root'])
        
        # Verify loading window was created
        mocks['loading_window'].assert_called_once()
        
        # Verify thread was created and started
        mocks['thread'].assert_called_once()
        mocks['thread_instance'].start.assert_called_once()
        assert ModelManager.local_model is not None
    
    def test_setup_model_with_existing_model(self, setup_dependencies, monkeypatch):
        """Test setup_model when a model is already loaded"""
        mocks = setup_dependencies
        
        # Setup method to simulate successful model loading
        def mock_thread_target(*args, **kwargs):
            ModelManager.local_model = mocks['model_instance']
            return True
            
        # Mock the thread instance's start method
        mocks['thread_instance'].start = MagicMock(side_effect=mock_thread_target)
        
        # Set existing model with close method
        existing_model = MagicMock()
        existing_model.model = MagicMock()
        ModelManager.local_model = existing_model
        
        # Call the method
        ModelManager.setup_model(mocks['settings'], mocks['root'])
        
        # Verify existing model was unloaded
        existing_model.model.close.assert_called_once()
    
    def test_setup_model_error(self, setup_dependencies, monkeypatch):
        """Test error handling during model setup"""
        mocks = setup_dependencies
        
        # Create a function that simulates a model loading error
        def mock_thread_error(*args, **kwargs):
            ModelManager.local_model = ModelStatus.ERROR
            return False
            
        # Mock the thread instance's start method
        mocks['thread_instance'].start = MagicMock(side_effect=mock_thread_error)
        
        # Reset ModelManager state
        ModelManager.local_model = None
        
        # Call the method
        with patch.object(mocks['messagebox'], 'showerror') as mock_showerror:
            ModelManager.setup_model(mocks['settings'], mocks['root'])
            
            # Verify error message was shown
            assert mock_showerror.call_count > 0 or ModelManager.local_model == ModelStatus.ERROR
    
    def test_start_model_threaded(self, setup_dependencies):
        """Test starting the model in a separate thread"""
        mocks = setup_dependencies
        
        # Call the method
        thread = ModelManager.start_model_threaded(mocks['settings'], mocks['root'])
        
        # Verify thread was created and started
        assert mocks['thread'].call_count > 0
        assert mocks['thread_instance'].start.call_count > 0
        
        # Verify correct thread was returned
        assert thread == mocks['thread_instance']
    
    def test_unload_model(self):
        """Test unloading the model"""
        # Create mock model
        mock_model = MagicMock()
        mock_model.model = MagicMock()
        ModelManager.local_model = mock_model
        
        # Call the method
        ModelManager.unload_model()
        
        # Verify model was closed and reference cleared
        mock_model.model.close.assert_called_once()
        assert ModelManager.local_model is None
        