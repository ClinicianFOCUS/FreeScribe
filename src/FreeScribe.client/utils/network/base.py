from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import httpx
from dataclasses import dataclass

class NetworkRequestError(Exception):
    """Custom exception for network request errors."""
    pass


@dataclass
class NetworkConfig:
    """Configuration for network requests."""
    host: str
    api_key: str
    verify_ssl: bool = True
    timeout: float = 60.0
    connect_timeout: float = 10.0
    
    def __post_init__(self):
        if self.host.endswith('/'):
            self.host = self.host[:-1]


class BaseNetworkClient:
    """Base class for network clients."""
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _create_client(self) -> httpx.AsyncClient:
        """Create and return an async HTTP client."""
        if self._client is None:
            timeout = httpx.Timeout(self.config.timeout, connect=self.config.connect_timeout)
            self._client = httpx.AsyncClient(timeout=timeout, verify=self.config.verify_ssl)
        return self._client
    
    async def _close_client(self):
        """Close the HTTP client if it exists."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception as e:
                print(f"Error closing client: {e}")
            finally:
                self._client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            await self._create_client()
        return self._client
