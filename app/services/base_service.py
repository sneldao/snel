import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseService:
    """
    Base class for services providing common functionality.
    """
    
    def __init__(self):
        """
        Initialize the base service.
        """
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def _call_api(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an API call with error handling.
        
        Args:
            method: HTTP method to use
            url: URL to call
            json: JSON data to send
            params: Query parameters
            headers: HTTP headers
            
        Returns:
            API response data
        """
        try:
            response = await self.http_client.request(
                method,
                url,
                json=json,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return {
                "success": False,
                "error": f"API call failed: {str(e)}"
            }
    
    async def close(self):
        """
        Clean up resources.
        """
        await self.http_client.aclose() 