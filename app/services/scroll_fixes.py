"""
Scroll-specific fixes for swap transactions.
"""
import logging
import re
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

# Scroll chain ID
SCROLL_CHAIN_ID = 534352

# Known working router addresses for Scroll
SCROLL_ROUTER_ADDRESSES = {
    "0x": "0xDef1C0ded9bec7F1a1670819833240f027b25EfF",  # 0x router on Scroll
    "kyber": "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Kyber router on Scroll
    "openocean": "0x6352a56caadc4f1e25cd6c75970fa768a3304e64"  # OpenOcean router on Scroll
}

# Token addresses that need special handling on Scroll
SCROLL_NATIVE_ETH = "0x5300000000000000000000000000000000000004"
SCROLL_USDC = "0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4"

def fix_scroll_quotes(quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply Scroll-specific fixes to quotes.
    
    Args:
        quotes: List of quotes to fix
        
    Returns:
        Fixed quotes
    """
    fixed_quotes = []
    
    for quote in quotes:
        # Skip quotes with unreasonable gas estimates
        gas = quote.get("gas")
        if gas and gas.isdigit() and int(gas) > 1000000:
            logger.warning(f"Skipping quote with unreasonable gas estimate: {gas}")
            continue
            
        # Fix router addresses
        aggregator = quote.get("aggregator")
        if aggregator and aggregator in SCROLL_ROUTER_ADDRESSES:
            quote["to"] = SCROLL_ROUTER_ADDRESSES[aggregator]
            
        # Fix value field for native ETH swaps
        token_in = quote.get("token_in_address", "")
        if token_in and token_in.lower() == SCROLL_NATIVE_ETH.lower():
            # For native ETH, ensure value field is set correctly
            if quote.get("value") == "0" or not quote.get("value"):
                quote["value"] = quote.get("sell_amount", "0")
                
        # Add the fixed quote
        fixed_quotes.append(quote)
    
    # If we have no quotes after filtering, try to be more lenient
    if not fixed_quotes and quotes:
        logger.warning("No quotes passed Scroll validation, using original quotes")
        return quotes
        
    return fixed_quotes

def fix_scroll_transaction(tx_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply Scroll-specific fixes to a transaction.
    
    Args:
        tx_data: Transaction data to fix
        
    Returns:
        Fixed transaction data
    """
    # Make a copy to avoid modifying the original
    fixed_tx = tx_data.copy()
    
    # Fix router address
    if "to" in fixed_tx:
        aggregator = fixed_tx.get("metadata", {}).get("aggregator")
        if aggregator and aggregator in SCROLL_ROUTER_ADDRESSES:
            fixed_tx["to"] = SCROLL_ROUTER_ADDRESSES[aggregator]
    
    # Fix gas limit - Scroll sometimes needs higher gas limits
    if "gas_limit" in fixed_tx:
        try:
            gas_limit = int(fixed_tx["gas_limit"])
            if gas_limit < 300000:
                logger.info(f"Increasing gas limit for Scroll: {gas_limit} -> 300000")
                fixed_tx["gas_limit"] = "300000"
        except (ValueError, TypeError):
            fixed_tx["gas_limit"] = "300000"
    
    # Fix value field for native ETH swaps
    token_in_address = fixed_tx.get("metadata", {}).get("token_in_address", "")
    if token_in_address and token_in_address.lower() == SCROLL_NATIVE_ETH.lower():
        # For native ETH, ensure value field is set correctly
        if fixed_tx.get("value") == "0" or not fixed_tx.get("value"):
            sell_amount = fixed_tx.get("metadata", {}).get("sell_amount", "0")
            fixed_tx["value"] = sell_amount
            logger.info(f"Fixed value field for native ETH swap: {sell_amount}")
    
    return fixed_tx

def get_recommended_aggregator(token_in: str, token_out: str) -> str:
    """
    Get the recommended aggregator for a token pair on Scroll.
    
    Args:
        token_in: Input token address
        token_out: Output token address
        
    Returns:
        Recommended aggregator name
    """
    # For ETH to USDC, 0x works best on Scroll
    if (token_in.lower() == SCROLL_NATIVE_ETH.lower() and 
        token_out.lower() == SCROLL_USDC.lower()):
        return "0x"
        
    # For USDC to ETH, 0x works best on Scroll
    if (token_in.lower() == SCROLL_USDC.lower() and 
        token_out.lower() == SCROLL_NATIVE_ETH.lower()):
        return "0x"
        
    # Default to 0x for most pairs
    return "0x"

def parse_scroll_error(error_message: str) -> str:
    """
    Parse Scroll-specific error messages.
    
    Args:
        error_message: Error message to parse
        
    Returns:
        User-friendly error message
    """
    # Check for common Scroll errors
    if "TRANSFER_FROM_FAILED" in error_message:
        return "Transaction failed: The token transfer failed. This usually happens when trying to swap ETH directly. Try using WETH instead."
        
    if "execution reverted" in error_message:
        return "Transaction failed on Scroll. This may be due to insufficient liquidity or high price impact."
        
    if "gas required exceeds allowance" in error_message:
        return "Transaction failed: Gas required exceeds allowance on Scroll. Try a smaller amount or use a different aggregator."
        
    # Default to original message
    return error_message

def apply_scroll_fixes(tx_data: Dict[str, Any], chain_id: int, swap_command=None) -> Dict[str, Any]:
    """
    Apply all Scroll-specific fixes to transaction data.
    
    Args:
        tx_data: Transaction data to fix
        chain_id: Chain ID
        swap_command: Optional swap command
        
    Returns:
        Fixed transaction data
    """
    if chain_id != SCROLL_CHAIN_ID:
        return tx_data
        
    logger.info("Applying Scroll-specific fixes to transaction data")
    
    # Make a copy to avoid modifying the original
    fixed_tx = tx_data.copy()
    
    # Fix quotes if present
    if "all_quotes" in fixed_tx:
        fixed_tx["all_quotes"] = fix_scroll_quotes(fixed_tx["all_quotes"])
        fixed_tx["quotes_count"] = len(fixed_tx["all_quotes"])
        
    # Fix transaction data
    if "to" in fixed_tx:
        fixed_tx = fix_scroll_transaction(fixed_tx)
        
    return fixed_tx
