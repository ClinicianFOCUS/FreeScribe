import requests
from urllib.parse import urlparse


class InvalidRequestException(Exception):
    """Custom exception for invalid secure requests."""
    def __init__(self, message):
        super().__init__(message)


def is_loopback_request(url):
    """
    Checks if a URL is a loopback address.
    
    Args:
        url (str): The URL to check.
    
    Returns:
        bool: True if the URL is a loopback address, False otherwise.
    """
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Check if the address is loopback
    if parsed_url.hostname not in ("localhost", "127.0.0.1", "::1"):
        return False
    
    return True

def is_https(url):
    """
    Checks if a URL uses HTTPS.
    
    Args:
        url (str): The URL to check.
    
    Returns:
        bool: True if the URL uses HTTPS, False otherwise.
    """
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Check if the URL uses HTTPS
    if parsed_url.scheme == "https":
        return True
    
    return False

def secure_post(url, data=None, **kwargs):
    """
    Sends a POST request to a URL using HTTPS.
    
    Args:
        url (str): The URL to send the request to.
        data (dict, optional): The data to send with the request.
        headers (dict, optional): The headers to include with the request.
    
    Returns:
        requests.Response: The response object.
    """
    # Check if the URL is a loopback address
    if not is_loopback_request(url) and not is_https(url):
        raise InvalidRequestException("Traffic not over loopback must be HTTPS.")
    
    # Send the POST request
    response = requests.post(url, data=data, **kwargs)
    
    return response

def secure_get(url, **kwargs):
    """
    Sends a GET request to a URL using HTTPS.
    
    Args:
        url (str): The URL to send the request to.
        headers (dict, optional): The headers to include with the request.
    
    Returns:
        requests.Response: The response object.
    """
    # Check if the URL is a loopback address
    if not is_loopback_request(url) and not is_https(url):
        raise InvalidRequestException("Traffic not over loopback must be HTTPS.")
    
    # Send the GET request
    response = requests.get(url, **kwargs)
    
    return response