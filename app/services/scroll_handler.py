"""
Handler for Scroll-specific operations.
"""
import logging
from typing import Dict, Any, List, Optional, Union

from app.services.scroll_fixes import (
    apply_scroll_fixes,
    get_recommended_aggregator,
    parse_scroll_error,
    SCROLL_CHAIN_ID
)
from app.services.brian_service import brian_service

logger = logging.getLogger(__name__)

class ScrollHandler:
    """
    Handler for Scroll-specific operations.
    
    This class provides static methods to handle Scroll-specific operations
    like fixing quotes, recommending aggregators, and parsing errors.
    """
    
    @staticmethod
    async def use_brian_api(swap_command, wallet_address, chain_id) -> Dict[str, Any]:
        """
        Use the Brian API to get a swap transaction for Scroll.
        
        Args:
            swap_command: The swap command
            wallet_address: The wallet address
            chain_id: The chain ID
            
        Returns:
            Transaction data from Brian API
        """
        if chain_id != SCROLL_CHAIN_ID:
            return None
            
        logger.info("Using Brian API for Scroll swap")
        try:
            # Check if Brian API key is set
            if not brian_service.api_key:
                logger.warning("BRIAN_API_KEY environment variable not set. Falling back to regular aggregators.")
                return None
                
            # Get swap transaction from Brian API
            tx_data = await brian_service.get_swap_transaction(
                swap_command=swap_command,
                wallet_address=wallet_address,
                chain_id=chain_id
            )
            
            # Validate the response
            if not tx_data or not tx_data.get("all_quotes"):
                logger.warning("Brian API returned invalid or empty response")
                return None
                
            logger.info(f"Got transaction data from Brian API: {tx_data}")
            return tx_data
        except ValueError as e:
            # Handle specific error cases
            error_msg = str(e)
            if "Invalid JSON response" in error_msg:
                logger.error(f"Brian API returned invalid JSON: {error_msg}")
            elif "HTTP" in error_msg:
                logger.error(f"Brian API HTTP error: {error_msg}")
            else:
                logger.error(f"Brian API value error: {error_msg}")
            return None
        except Exception as e:
            logger.error(f"Error using Brian API for Scroll swap: {str(e)}")
            return None
    
    @staticmethod
    def apply_scroll_fixes(tx_data: Dict[str, Any], chain_id: int, swap_command=None) -> Dict[str, Any]:
        """
        Apply Scroll-specific fixes to transaction data.
        
        Args:
            tx_data: Transaction data to fix
            chain_id: Chain ID
            swap_command: Optional swap command
            
        Returns:
            Fixed transaction data
        """
        logger.info("Applying Scroll-specific fixes to transaction data")
        return apply_scroll_fixes(tx_data, chain_id, swap_command)
    
    @staticmethod
    def get_recommended_aggregator(token_in: str, token_out: str, chain_id: int) -> Optional[str]:
        """
        Get the recommended aggregator for a token pair on Scroll.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            chain_id: Chain ID
            
        Returns:
            Recommended aggregator name or None if not on Scroll
        """
        if chain_id != SCROLL_CHAIN_ID:
            return None
            
        # For Scroll, we now recommend Brian as the default aggregator
        return "brian"
    
    @staticmethod
    def parse_scroll_error(error_message: str, chain_id: int) -> str:
        """
        Parse Scroll-specific error messages.
        
        Args:
            error_message: Error message to parse
            chain_id: Chain ID
            
        Returns:
            User-friendly error message
        """
        if chain_id != SCROLL_CHAIN_ID:
            return error_message
            
        return parse_scroll_error(error_message)
    
    @staticmethod
    def handle_scroll_error(error_message: str, chain_id: int) -> str:
        """
        Handle Scroll-specific error messages.
        
        Args:
            error_message: Error message to handle
            chain_id: Chain ID
            
        Returns:
            User-friendly error message
        """
        if chain_id != SCROLL_CHAIN_ID:
            return error_message
            
        return parse_scroll_error(error_message)
    
    @staticmethod
    def is_scroll_chain(chain_id: int) -> bool:
        """
        Check if the chain is Scroll.
        
        Args:
            chain_id: Chain ID
            
        Returns:
            True if the chain is Scroll, False otherwise
        """
        return chain_id == SCROLL_CHAIN_ID
    
    @staticmethod
    def get_native_eth_address() -> str:
        """
        Get the native ETH address on Scroll.
        
        Returns:
            Native ETH address on Scroll
        """
        return "0x5300000000000000000000000000000000000004"
