# utils/whisper_utils.py
import logging
import threading
import time
from urllib.parse import urlparse
import requests
from UI.LoadingWindow import LoadingWindow
from UI.Widgets.PopupBox import PopupBox


def validate_whisper_endpoint(settings, parent_window, endpoint_url, verify_ssl, api_key):
    """
    Validates connectivity to the Whisper speech-to-text endpoint and prompts the user if validation fails.
    
    Shows a loading window during the validation process and displays a prompt 
    dialog if the connection fails, allowing the user to proceed or cancel.

    Args:
        settings: The settings object containing application configuration.
        parent_window: The parent window for displaying UI components.
        endpoint_url (str): The URL of the Whisper endpoint to validate.
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

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            try:
                # Send empty request to check endpoint availability
                # This should return a 400 or 422 error for missing file
                response = requests.post(endpoint_url, headers=headers, json={}, verify=verify_ssl)

                # Check for expected response codes
                # 400/422 indicate server is up but rejecting empty request (expected behavior)
                if response.status_code in {400, 422}:
                    json_response = response.json()
                    result_container["result"] = "detail" in json_response
                    if not result_container["result"]:
                        result_container["error_message"] = f"Server responded with unexpected format (status code: {response.status_code})"
                elif response.status_code == 401 or response.status_code == 403:
                    result_container["result"] = False
                    result_container["error_message"] = "Authentication failed. Please check your API key."
                else:
                    result_container["result"] = response.status_code < 400
                    if not result_container["result"]:
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
            logging.exception("Error while validating Whisper endpoint")
            result_container["result"] = False
            result_container["error_message"] = f"Unexpected error: {str(e)}"
        finally:
            result_container["done"] = True
    
    try:
        # Create loading window
        loading = LoadingWindow(
            parent=parent_window,
            title="Checking Connection",
            initial_text="Checking Whisper endpoint connection...",
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
                message=f"Unable to connect to the Whisper endpoint at: {endpoint_url}\n\nError details: {error_details}\n\nWould you like to proceed with saving anyway?",
                title="Connection Error",
                button_text_1="Continue",
                button_text_2="Cancel"
            )
            return popup.response == "button_1"  # Return True if Continue, False if Cancel
        
        # Endpoint is reachable
        return True
    
    except Exception as e:
        logging.exception("Exception in validate_whisper_endpoint UI handling")
        # Return True on exception to allow the process to continue
        return True