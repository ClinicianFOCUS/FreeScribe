"""
/utils/network/base.py

This software is released under the AGPL-3.0 license
Copyright (c) 2023-2024 Braedon Hendy

Further updates and packaging added in 2024 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform". 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students - Software Developer Alex Simko, Pemba Sherpa (F24), and Naitik Patel.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import httpx
from dataclasses import dataclass
from utils.log_config import logger

class NetworkRequestError(Exception):
    """Custom exception for network request errors."""
    pass


@dataclass
class NetworkConfig:
    """Configuration for network requests.
    
    This dataclass holds the configuration parameters needed for making
    network requests, including host information, authentication, and
    connection settings.
    
    :param host: The base URL or hostname for the API endpoint
    :type host: str
    :param api_key: Authentication key for API access
    :type api_key: str
    :param verify_ssl: Whether to verify SSL certificates during requests
    :type verify_ssl: bool
    :param timeout: General timeout for network operations in seconds
    :type timeout: float
    :param connect_timeout: Connection timeout in seconds
    :type connect_timeout: float
    """
    host: str
    api_key: str
    verify_ssl: bool = True
    timeout: float = 60.0
    connect_timeout: float = 10.0
    
    def __post_init__(self):
        """Normalize the host URL by removing trailing slashes.
        
        This method is automatically called after initialization to ensure
        the host URL is properly formatted without trailing slashes.
        """
        self.host = self.host.rstrip('/')


class BaseNetworkClient:
    """Base class for network clients.
    
    This class provides a foundation for creating network clients with
    proper connection management and resource cleanup. It handles the
    creation and lifecycle of HTTP clients using httpx.
    """
    
    def __init__(self, config: NetworkConfig):
        """Initialize the network client with configuration.
        
        :param config: Network configuration containing connection parameters
        :type config: NetworkConfig
        """
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _create_client(self) -> httpx.AsyncClient:
        """Create and return an async HTTP client.
        
        Creates a new httpx.AsyncClient instance with timeout and SSL
        verification settings based on the provided configuration. The
        client is cached for reuse.
        
        :return: Configured async HTTP client
        :rtype: httpx.AsyncClient
        """
        if self._client is None:
            timeout = httpx.Timeout(self.config.timeout, connect=self.config.connect_timeout, read=self.config.timeout, write=self.config.timeout, pool=self.config.timeout)
            self._client = httpx.AsyncClient(timeout=timeout, verify=self.config.verify_ssl)
        return self._client
    
    async def _close_client(self):
        """Close the HTTP client if it exists.
        
        Properly closes the httpx.AsyncClient to free up resources and
        connections. Any exceptions during closure are logged but not
        re-raised to ensure cleanup completes.
        
        :raises Exception: Logs but does not re-raise exceptions during client closure
        """
        if self._client:
            try:
                await self._client.aclose()
            except Exception as e:
                logger.exception(f"Error closing client: {e}")
            finally:
                self._client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.
        
        Returns the existing HTTP client if available, otherwise creates
        a new one. This method ensures lazy initialization of the client.
        
        :return: Active HTTP client instance
        :rtype: httpx.AsyncClient
        """
        if self._client is None:
            await self._create_client()
        return self._client
