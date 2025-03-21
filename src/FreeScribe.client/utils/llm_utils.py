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
    result_container = {"result": False, "done": False}
    
    # Define the worker function to run in a separate thread
    def worker_thread():
        try:
            parsed_url = urlparse(endpoint_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                result_container["result"] = False
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
                    except json.JSONDecodeError:
                        result_container["result"] = False
                else:
                    result_container["result"] = False

            except requests.exceptions.RequestException:
                result_container["result"] = False

        except Exception:
            result_container["result"] = False
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
            # Show error popup
            popup = PopupBox(
                parent=parent_window,
                message=f"Unable to connect to the LLM endpoint at: {endpoint_url}.\nWould you like to proceed with saving anyway?",
                title="Connection Error",
                button_text_1="Continue",
                button_text_2="Cancel"
            )
            return popup.response == "button_1"  # Return True if Continue, False if Cancel
        
        # Endpoint is reachable
        return True
    
    except Exception:
        # Return True on exception to allow the process to continue
        return True