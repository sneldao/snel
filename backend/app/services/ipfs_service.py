"""
IPFS service for decentralized storage of AI research logs and portfolio insights.
Supports pinning to IPFS gateways and retrieving data via CIDs.
"""

import json
import logging
import os
import aiohttp
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class IPFSService:
    """
    Service for IPFS operations.
    """

    def __init__(self) -> None:
        """Initialize with IPFS gateway and optional API keys."""
        # For hackathon, use a public gateway or an environment-specific one
        self.gateway_url = os.getenv("IPFS_GATEWAY", "https://gateway.ipfs.io/ipfs/")
        self.pinata_api_key = os.getenv("PINATA_API_KEY")
        self.pinata_secret_key = os.getenv("PINATA_SECRET_KEY")
        
        # If no Pinata keys, we'll log warnings but still function (limited)
        if not self.pinata_api_key:
            logger.warning("PINATA_API_KEY not set. IPFS pinning will be unavailable.")

    async def upload_json(self, data: Dict[str, Any], filename: str = "research_log.json") -> Optional[str]:
        """
        Upload JSON data to IPFS via Pinata.
        
        Args:
            data: The JSON-serializable data to upload.
            filename: Metadata filename for the pin.
            
        Returns:
            The IPFS CID if successful, None otherwise.
        """
        if not self.pinata_api_key or not self.pinata_secret_key:
            logger.error("Cannot upload to IPFS: Pinata credentials missing.")
            return None

        url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
        headers = {
            "pinata_api_key": self.pinata_api_key,
            "pinata_secret_api_key": self.pinata_secret_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "pinataContent": data,
            "pinataMetadata": {
                "name": filename
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        res_json = await response.json()
                        cid = res_json.get("IpfsHash")
                        logger.info(f"Successfully pinned to IPFS: {cid}")
                        return cid
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to pin to IPFS (Status {response.status}): {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error uploading to IPFS: {e}")
            return None

    async def get_json(self, cid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve JSON data from IPFS via gateway.
        """
        url = f"{self.gateway_url}{cid}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to fetch from IPFS: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching from IPFS: {e}")
            return None

# Singleton instance
ipfs_service = IPFSService()
