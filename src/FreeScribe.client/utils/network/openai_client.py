import asyncio
import json
import httpx
from typing import Dict, Any, Optional, List
from .base import BaseNetworkClient, NetworkConfig, NetworkRequestError
from utils.log_config import logger


class OpenAIClient(BaseNetworkClient):
    """Client for communicating with OpenAI API."""
    
    def __init__(self, config: NetworkConfig):
        super().__init__(config)
    
    async def send_chat_completion(
        self, 
        text: str, 
        model: str, 
        stop_event: asyncio.Event,
        system_message: Optional[str] = None,
        **options
    ) -> str:
        """
        Sends text to OpenAI API using httpx AsyncClient in a cancellable async format.
        
        Args:
            text (str): The text to send to the API
            model (str): The model name to use (e.g., 'gpt-4', 'gpt-3.5-turbo')
            stop_event (asyncio.Event): Event to signal cancellation
            system_message (str, optional): System message to set context
            **options: Additional model options (temperature, max_tokens, etc.)
            
        Returns:
            str: The response text or 'Error' if cancelled/failed
        """
        try:
            # Check for cancellation before starting
            if stop_event.is_set():
                return 'Error: Operation cancelled'
            
            # Create httpx client
            self._client = await self._create_client()
            
            # Check for cancellation after client creation
            if stop_event.is_set():
                return 'Error: Operation cancelled'

            # Prepare payload for OpenAI API
            payload = self._build_payload(text, model, system_message, **options)

            # Check for cancellation before sending request
            if stop_event.is_set():
                return 'Error: Operation cancelled'

            # Send POST request to OpenAI chat endpoint
            response = await self._send_request(payload)
            
            # Check for cancellation after response
            if stop_event.is_set():
                return 'Error: Operation cancelled'
            
            # Extract and return response text
            return self._parse_response(response)

        except Exception as e:
            error_message = self._handle_error(e)
            logger.exception(f"Error in OpenAI API call: {e}")
            return f'Error: {error_message}'
        
        finally:
            await self._close_client()
    
    async def send_completion(
        self, 
        prompt: str, 
        model: str, 
        stop_event: asyncio.Event,
        **options
    ) -> str:
        """
        Sends text to OpenAI Completion API (for older models like text-davinci-003).
        
        Args:
            prompt (str): The prompt to send to the API
            model (str): The model name to use
            stop_event (asyncio.Event): Event to signal cancellation
            **options: Additional model options
            
        Returns:
            str: The response text or 'Error' if cancelled/failed
        """
        try:
            if stop_event.is_set():
                return 'Error: Operation cancelled'
            
            self._client = await self._create_client()
            
            if stop_event.is_set():
                return 'Error: Operation cancelled'

            payload = self._build_completion_payload(prompt, model, **options)

            if stop_event.is_set():
                return 'Error: Operation cancelled'

            response = await self._send_completion_request(payload)
            
            if stop_event.is_set():
                return 'Error: Operation cancelled'
            
            return self._parse_completion_response(response)

        except Exception as e:
            error_message = self._handle_error(e)
            logger.exception(f"Error in OpenAI Completion API call: {e}")
            return f'Error: {error_message}'
        
        finally:
            await self._close_client()
    
    def _build_payload(
        self, 
        text: str, 
        model: str, 
        system_message: Optional[str] = None,
        **options
    ) -> Dict[str, Any]:
        """Build the request payload for OpenAI Chat API."""
        messages = []
        
        # Add system message if provided
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        # Add user message
        messages.append({"role": "user", "content": text})
        
        payload = {
            "model": model.strip(),
            "messages": messages
        }
        
        # Add options with validation
        try:
            if 'temperature' in options and options['temperature'] is not None:
                payload["temperature"] = float(options['temperature'])
            if 'max_tokens' in options and options['max_tokens'] is not None:
                payload["max_tokens"] = int(options['max_tokens'])
            if 'top_p' in options and options['top_p'] is not None:
                payload["top_p"] = float(options['top_p'])
            if 'frequency_penalty' in options and options['frequency_penalty'] is not None:
                payload["frequency_penalty"] = float(options['frequency_penalty'])
            if 'presence_penalty' in options and options['presence_penalty'] is not None:
                payload["presence_penalty"] = float(options['presence_penalty'])
            if 'stop' in options and options['stop'] is not None:
                payload["stop"] = options['stop']  # Can be string or list
            if 'stream' in options and options['stream'] is not None:
                payload["stream"] = bool(options['stream'])
                
        except ValueError as e:
            logger.exception(f"Error parsing options: {e}. Using defaults.")
            # Set reasonable defaults for OpenAI
            payload.update({
                "temperature": 0.7,
                "max_tokens": 1000,
                "top_p": 1.0
            })
        
        return payload
    
    def _build_completion_payload(self, prompt: str, model: str, **options) -> Dict[str, Any]:
        """Build the request payload for OpenAI Completion API."""
        payload = {
            "model": model.strip(),
            "prompt": prompt
        }
        
        try:
            if 'temperature' in options and options['temperature'] is not None:
                payload["temperature"] = float(options['temperature'])
            if 'max_tokens' in options and options['max_tokens'] is not None:
                payload["max_tokens"] = int(options['max_tokens'])
            if 'top_p' in options and options['top_p'] is not None:
                payload["top_p"] = float(options['top_p'])
            if 'frequency_penalty' in options and options['frequency_penalty'] is not None:
                payload["frequency_penalty"] = float(options['frequency_penalty'])
            if 'presence_penalty' in options and options['presence_penalty'] is not None:
                payload["presence_penalty"] = float(options['presence_penalty'])
            if 'stop' in options and options['stop'] is not None:
                payload["stop"] = options['stop']
                
        except ValueError as e:
            logger.exception(f"Error parsing completion options: {e}")
            payload.update({
                "temperature": 0.7,
                "max_tokens": 1000
            })
        
        return payload
    
    async def _send_request(self, payload: Dict[str, Any]) -> httpx.Response:
        """Send the HTTP request to the OpenAI Chat API."""
        url = f"{self.config.host}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        
        response = await self._client.post(url, json=payload, headers=headers)
        return response
    
    async def _send_completion_request(self, payload: Dict[str, Any]) -> httpx.Response:
        """Send the HTTP request to the OpenAI Completion API."""
        url = f"{self.config.host}/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        
        response = await self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response
    
    def _parse_response(self, response: httpx.Response) -> str:
        """Parse the response from OpenAI Chat API."""
        response_data = response.json()
        logger.debug(f"OpenAI Chat Response: {json.dumps(response_data, indent=2)}")
        
        try:
            return response_data['choices'][0]['message']['content']
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing OpenAI response structure: {e}")
            logger.error(f"Response data: {response_data}")
            return 'Error: Invalid response format from OpenAI API'
    
    def _parse_completion_response(self, response: httpx.Response) -> str:
        """Parse the response from OpenAI Completion API."""
        response_data = response.json()
        logger.debug(f"OpenAI Completion Response: {json.dumps(response_data, indent=2)}")
        
        try:
            return response_data['choices'][0]['text'].strip()
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing OpenAI completion response structure: {e}")
            logger.error(f"Response data: {response_data}")
            return 'Error: Invalid response format from OpenAI Completion API'
    
    def _handle_error(self, error: Exception) -> str:
        """Handle and categorize different types of errors specific to OpenAI."""
        if isinstance(error, httpx.ReadError):
            return f"Network connection lost to OpenAI API. Please check your internet connection."
        elif isinstance(error, httpx.ConnectError):
            return f"Cannot connect to OpenAI API. Please check your internet connection."
        elif isinstance(error, httpx.TimeoutException):
            return f"Request timed out to OpenAI API. Please try again."
        elif isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            if status_code == 401:
                return "Invalid OpenAI API key. Please check your API key."
            elif status_code == 429:
                return "OpenAI API rate limit exceeded. Please wait and try again."
            elif status_code == 400:
                return f"Bad request to OpenAI API: {error.response.text}"
            elif status_code == 404:
                return "OpenAI API endpoint not found. Please check the model name."
            else:
                return f"OpenAI API error {status_code}: {error.response.text}"
        else:
            return f"OpenAI API request failed: {str(error)}"
    
    async def cancel_request(self):
        """Cancel an ongoing API request by setting the stop event and closing the client."""
        try:
            logger.info("Cancelling OpenAI API request...")
            await self._close_client()
            logger.info("OpenAI API request cancelled successfully.")
        except Exception as e:
            logger.exception(f"Error during OpenAI API cancellation: {e}")