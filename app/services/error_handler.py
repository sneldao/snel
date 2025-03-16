"""
Error handling for transaction execution.
"""
import logging
from typing import Dict, Any, Optional
import json
import re

logger = logging.getLogger(__name__)

# Common error patterns
INSUFFICIENT_FUNDS_PATTERN = re.compile(r"(insufficient funds|not enough balance)", re.IGNORECASE)
SLIPPAGE_PATTERN = re.compile(r"(slippage|price impact|price movement|price changed)", re.IGNORECASE)
TRANSFER_FAILED_PATTERN = re.compile(r"(transfer from failed|transferfrom failed|transfer failed)", re.IGNORECASE)
GAS_ESTIMATION_PATTERN = re.compile(r"(cannot estimate gas|gas required exceeds|gas limit)", re.IGNORECASE)
TIMEOUT_PATTERN = re.compile(r"(timeout|timed out|deadline)", re.IGNORECASE)
NONCE_PATTERN = re.compile(r"(nonce|transaction underpriced|replacement transaction)", re.IGNORECASE)

def handle_transaction_error(error: Exception) -> Dict[str, Any]:
    """
    Handle transaction execution errors and return a user-friendly response.
    
    Args:
        error: The exception that occurred
        
    Returns:
        Dictionary with error information
    """
    error_message = str(error)
    logger.error(f"Transaction error: {error_message}")
    
    # Try to extract JSON error if present
    json_error = extract_json_error(error_message)
    if json_error:
        error_message = json_error
    
    # Check for specific error types
    if INSUFFICIENT_FUNDS_PATTERN.search(error_message):
        return {
            "success": False,
            "error": "Insufficient funds to complete this transaction. Please check your balance.",
            "error_type": "insufficient_funds",
            "original_error": error_message
        }
    
    if SLIPPAGE_PATTERN.search(error_message):
        return {
            "success": False,
            "error": "Price changed during transaction. Try again with higher slippage tolerance.",
            "error_type": "slippage",
            "original_error": error_message
        }
    
    if TRANSFER_FAILED_PATTERN.search(error_message):
        return {
            "success": False,
            "error": "Token transfer failed. This may be due to insufficient balance or allowance.",
            "error_type": "transfer_failed",
            "original_error": error_message
        }
    
    if GAS_ESTIMATION_PATTERN.search(error_message):
        return {
            "success": False,
            "error": "Failed to estimate gas. Try a different token amount or aggregator.",
            "error_type": "gas_estimation",
            "original_error": error_message
        }
    
    if TIMEOUT_PATTERN.search(error_message):
        return {
            "success": False,
            "error": "Transaction timed out. Please try again.",
            "error_type": "timeout",
            "original_error": error_message
        }
    
    if NONCE_PATTERN.search(error_message):
        return {
            "success": False,
            "error": "Transaction nonce issue. Please try again.",
            "error_type": "nonce",
            "original_error": error_message
        }
    
    # Default error response
    return {
        "success": False,
        "error": "Transaction failed. Please try again or try a different amount.",
        "error_type": "unknown",
        "original_error": error_message
    }

def extract_json_error(error_message: str) -> Optional[str]:
    """
    Extract JSON error message from error string if present.
    
    Args:
        error_message: The error message to parse
        
    Returns:
        Extracted error message or None if not found
    """
    # Try to find JSON in the error message
    json_start = error_message.find('{')
    json_end = error_message.rfind('}')
    
    if json_start >= 0 and json_end > json_start:
        try:
            json_str = error_message[json_start:json_end+1]
            error_data = json.loads(json_str)
            
            # Check for common error message fields
            if 'message' in error_data:
                return error_data['message']
            elif 'error' in error_data and isinstance(error_data['error'], dict):
                if 'message' in error_data['error']:
                    return error_data['error']['message']
            elif 'error' in error_data and isinstance(error_data['error'], str):
                return error_data['error']
            
        except json.JSONDecodeError:
            pass
    
    return None

def parse_chain_specific_error(error_message: str, chain_id: int) -> str:
    """
    Parse chain-specific error messages.
    
    Args:
        error_message: The error message to parse
        chain_id: The chain ID
        
    Returns:
        Parsed error message
    """
    # Scroll chain
    if chain_id == 534352:
        from app.services.scroll_fixes import parse_scroll_error
        return parse_scroll_error(error_message)
    
    # Base chain
    if chain_id == 8453:
        if "gas required exceeds allowance" in error_message:
            return "Transaction failed: Gas required exceeds allowance on Base. Try a smaller amount."
    
    # Default to original message
    return error_message
