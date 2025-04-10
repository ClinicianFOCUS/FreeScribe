# utils/llm_utils.py
import json
import logging
import threading
import time
from urllib.parse import urlparse
import requests
from UI.LoadingWindow import LoadingWindow
from UI.Widgets.PopupBox import PopupBox


def validate_llm_endpoint(settings, parent_window, endpoint_url, verify_ssl, api_key):
    """
    Validates connectivity to the LLM endpoint and prompts the user if validation fails.
    
    Shows a loading window during the validation process and displays a prompt 
    dialog if the connection fails, allowing the user to proceed or cancel.

    Args:
        settings: The settings object containing application configuration.
        parent_window: The parent window for displaying UI components.
        endpoint_url (str): The URL of the LLM endpoint to validate.
        verify_ssl (bool): Whether to verify SSL certificates.
        api_key (str): The API key for authorization.

    Returns:
        bool: True if the endpoint is reachable or user chooses to proceed anyway,
            False if the endpoint is not reachable and user cancels.
    """
    # Create a result container to share data between threads
    result_container = {"result": False, "done": False, "error_message": ""}
    
    # Define the worker function to run in a separate thread
    def worker_thread():
        try:
            # Check if API key is provided
            if not api_key:
                result_container["result"] = False
                result_container["error_message"] = "API key is missing or empty. Please provide a valid API key."
                result_container["done"] = True
                return

            parsed_url = urlparse(endpoint_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                result_container["result"] = False
                result_container["error_message"] = "Invalid URL format. Please provide a complete URL."
                result_container["done"] = True
                return

            # Construct models endpoint URL
            models_url = endpoint_url.rstrip('/') + '/models'
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.get(models_url, headers=headers, verify=verify_ssl)

                if response.status_code == 200:
                    try:
                        json_response = response.json()
                        # Check for expected OpenAI API response structure
                        result_container["result"] = (
                            "object" in json_response and 
                            json_response["object"] == "list" and 
                            "data" in json_response
                        )
                        if not result_container["result"]:
                            result_container["error_message"] = "Server response does not match expected OpenAI API format."
                    except json.JSONDecodeError:
                        result_container["result"] = False
                        result_container["error_message"] = "Server returned invalid JSON response."
                elif response.status_code == 401 or response.status_code == 403:
                    result_container["result"] = False
                    result_container["error_message"] = "Authentication failed. Please check your API key."
                else:
                    result_container["result"] = False
                    result_container["error_message"] = f"Server responded with error code: {response.status_code}"

            except requests.exceptions.SSLError:
                result_container["result"] = False
                result_container["error_message"] = "SSL certificate verification failed. Try Enabling self-signed certificate."
            except requests.exceptions.ConnectionError:
                result_container["result"] = False
                result_container["error_message"] = "Could not connect to server. Please check your network connection and endpoint URL."
            except requests.exceptions.Timeout:
                result_container["result"] = False
                result_container["error_message"] = "Connection timed out. The server may be slow or unreachable."
            except requests.exceptions.RequestException as e:
                result_container["result"] = False
                result_container["error_message"] = f"Request failed: {str(e)}"

        except Exception as e:
            logging.exception("Error while validating LLM endpoint")
            result_container["result"] = False
            result_container["error_message"] = f"Unexpected error: {str(e)}"
        finally:
            result_container["done"] = True
    
    try:
        # Create loading window
        loading = LoadingWindow(
            parent=parent_window,
            title="Checking Connection",
            initial_text="Checking LLM endpoint connection...",
            note_text="This may take a few seconds."
        )
        
        # Start the worker thread
        thread = threading.Thread(target=worker_thread)
        thread.daemon = True
        thread.start()
        
        # Keep updating the UI while the thread is working
        while not result_container["done"]:
            if parent_window and hasattr(parent_window, 'update'):
                parent_window.update()
            time.sleep(0.1)  # Small delay to prevent UI freezing
        
        # Close the loading window
        loading.destroy()
        
        # If endpoint is not reachable, prompt the user
        if not result_container["result"]:
            # Get the error message or use a default
            error_details = result_container.get("error_message", "Unknown connection error")
            
            # Show error popup with specific error details
            popup = PopupBox(
                parent=parent_window,
                message=f"Unable to connect to the LLM endpoint at: {endpoint_url}\n\nError details: {error_details}\n\nWould you like to proceed with saving anyway?",
                title="Connection Error",
                button_text_1="Continue",
                button_text_2="Cancel"
            )
            return popup.response == "button_1"  # Return True if Continue, False if Cancel
        
        # Endpoint is reachable
        return True
    
    except Exception as e:
        logging.exception("Exception in validate_llm_endpoint UI handling")
        # Return True on exception to allow the process to continue
        return True