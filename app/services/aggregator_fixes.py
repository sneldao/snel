"""
Chain-specific fixes for aggregator quotes.
"""
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

# Chain IDs
ETHEREUM_CHAIN_ID = 1
OPTIMISM_CHAIN_ID = 10
POLYGON_CHAIN_ID = 137
ARBITRUM_CHAIN_ID = 42161
BASE_CHAIN_ID = 8453
SCROLL_CHAIN_ID = 534352

def fix_quote_for_chain(
    quote: Dict[str, Any],
    chain_id: int,
    aggregator_name: str,
    token_out_decimals: int
) -> Dict[str, Any]:
    """
    Apply chain-specific fixes to a quote.
    
    Args:
        quote: The quote to fix
        chain_id: The chain ID
        aggregator_name: The aggregator name
        token_out_decimals: The decimals of the output token
        
    Returns:
        Fixed quote
    """
    # Make a copy to avoid modifying the original
    fixed_quote = quote.copy()
    
    # Apply chain-specific fixes
    if chain_id == SCROLL_CHAIN_ID:
        fixed_quote = _fix_scroll_quote(fixed_quote, aggregator_name, token_out_decimals)
    elif chain_id == BASE_CHAIN_ID:
        fixed_quote = _fix_base_quote(fixed_quote, aggregator_name, token_out_decimals)
    
    # Apply general fixes
    fixed_quote = _apply_general_fixes(fixed_quote, aggregator_name)
    
    return fixed_quote

def should_include_quote(
    quote: Dict[str, Any],
    chain_id: int,
    aggregator_name: str
) -> bool:
    """
    Determine if a quote should be included in the results.
    
    Args:
        quote: The quote to check
        chain_id: The chain ID
        aggregator_name: The aggregator name
        
    Returns:
        True if the quote should be included, False otherwise
    """
    # Check for required fields
    required_fields = ["to", "data", "value", "buy_amount", "sell_amount"]
    for field in required_fields:
        if field not in quote or not quote[field]:
            logger.warning(f"Quote missing required field: {field}")
            return False
    
    # Check for unreasonable gas estimates
    gas = quote.get("gas")
    if gas and gas.isdigit() and int(gas) > 10000000:  # 10M gas is definitely unreasonable
        logger.warning(f"Quote has unreasonable gas estimate: {gas}")
        return False
    
    # Check for zero buy amount
    buy_amount = quote.get("buy_amount")
    if buy_amount and buy_amount.isdigit() and int(buy_amount) == 0:
        logger.warning("Quote has zero buy amount")
        return False
    
    # Chain-specific checks
    if chain_id == SCROLL_CHAIN_ID:
        return _should_include_scroll_quote(quote, aggregator_name)
    
    # Default to including the quote
    return True

def _fix_scroll_quote(
    quote: Dict[str, Any],
    aggregator_name: str,
    token_out_decimals: int
) -> Dict[str, Any]:
    """
    Apply Scroll-specific fixes to a quote.
    
    Args:
        quote: The quote to fix
        aggregator_name: The aggregator name
        token_out_decimals: The decimals of the output token
        
    Returns:
        Fixed quote
    """
    # Fix gas estimates for Scroll
    gas = quote.get("gas")
    if gas and gas.isdigit():
        gas_int = int(gas)
        if gas_int > 1000000:
            logger.warning(f"Capping unreasonable Scroll gas estimate: {gas_int} -> 500000")
            quote["gas"] = "500000"
    
    # Fix router addresses for Scroll
    if aggregator_name == "0x":
        quote["to"] = "0xdef1c0ded9bec7f1a1670819833240f027b25eff"
    elif aggregator_name == "kyber":
        quote["to"] = "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5"
    elif aggregator_name == "openocean":
        quote["to"] = "0x6352a56caadc4f1e25cd6c75970fa768a3304e64"
    
    return quote

def _fix_base_quote(
    quote: Dict[str, Any],
    aggregator_name: str,
    token_out_decimals: int
) -> Dict[str, Any]:
    """
    Apply Base-specific fixes to a quote.
    
    Args:
        quote: The quote to fix
        aggregator_name: The aggregator name
        token_out_decimals: The decimals of the output token
        
    Returns:
        Fixed quote
    """
    # Fix gas estimates for Base
    gas = quote.get("gas")
    if gas and gas.isdigit():
        gas_int = int(gas)
        if gas_int > 1000000:
            logger.warning(f"Capping unreasonable Base gas estimate: {gas_int} -> 500000")
            quote["gas"] = "500000"
    
    return quote

def _apply_general_fixes(
    quote: Dict[str, Any],
    aggregator_name: str
) -> Dict[str, Any]:
    """
    Apply general fixes to a quote.
    
    Args:
        quote: The quote to fix
        aggregator_name: The aggregator name
        
    Returns:
        Fixed quote
    """
    # Ensure value is a string
    if "value" in quote and not isinstance(quote["value"], str):
        quote["value"] = str(quote["value"])
    
    # Ensure gas is a string
    if "gas" in quote and not isinstance(quote["gas"], str):
        quote["gas"] = str(quote["gas"])
    
    # Ensure buy_amount is a string
    if "buy_amount" in quote and not isinstance(quote["buy_amount"], str):
        quote["buy_amount"] = str(quote["buy_amount"])
    
    # Ensure sell_amount is a string
    if "sell_amount" in quote and not isinstance(quote["sell_amount"], str):
        quote["sell_amount"] = str(quote["sell_amount"])
    
    return quote

def _should_include_scroll_quote(
    quote: Dict[str, Any],
    aggregator_name: str
) -> bool:
    """
    Determine if a Scroll quote should be included in the results.
    
    Args:
        quote: The quote to check
        aggregator_name: The aggregator name
        
    Returns:
        True if the quote should be included, False otherwise
    """
    # Check for unreasonable gas estimates specific to Scroll
    gas = quote.get("gas")
    if gas and gas.isdigit() and int(gas) > 1000000:
        logger.warning(f"Scroll quote has unreasonable gas estimate: {gas}")
        return False
    
    # Check for empty or invalid data
    data = quote.get("data")
    if not data or len(data) < 10:  # Arbitrary minimum length for valid transaction data
        logger.warning(f"Scroll quote has invalid data: {data}")
        return False
    
    # Default to including the quote
    return True
