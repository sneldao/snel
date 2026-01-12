"""
Shared command extraction utilities for consistent parsing across processors.

Single source of truth for extracting addresses, tokens, amounts, and chains
from user input. Follows DRY principle.
"""
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def extract_address(text: str) -> Optional[str]:
    """
    Extract an Ethereum address or ENS name from text.
    
    Returns the first match of either:
    - Ethereum address: 0x followed by 40 hex chars
    - ENS name: word.eth pattern
    
    Args:
        text: Text to search
        
    Returns:
        Address or ENS name, or None if not found
    """
    if not text:
        return None
    
    # Check for Ethereum address (0x followed by 40 hex chars)
    eth_match = re.search(r'0x[a-fA-F0-9]{40}', text)
    if eth_match:
        return eth_match.group(0)
    
    # Check for ENS name (word.eth)
    ens_match = re.search(r'(\w+\.eth)', text, re.IGNORECASE)
    if ens_match:
        return ens_match.group(1)
    
    return None


async def extract_and_resolve_address(
    text: str,
    token_query_service,
    chain_id: int = 1
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract an address/ENS from text AND resolve it to a checksum address.
    
    Uses token_query_service to resolve ENS names and validate addresses.
    
    Args:
        text: Text to search
        token_query_service: Service instance for resolution
        chain_id: Chain ID for context
        
    Returns:
        Tuple of (resolved_address, display_name) where:
        - resolved_address: Checksum Ethereum address or None
        - display_name: Original ENS name if ENS, else the address
    """
    extracted = extract_address(text)
    if not extracted:
        return None, None
    
    # Use token_query_service to resolve and validate
    resolved, display = token_query_service.resolve_address(extracted, chain_id)
    return resolved, display


def extract_amount(text: str) -> Optional[str]:
    """
    Extract a numeric amount from text.
    
    Looks for number patterns like: "100", "100.5", "0.01"
    Optionally followed by a token symbol.
    
    Args:
        text: Text to search
        
    Returns:
        The number as a string, or None if not found
    """
    if not text:
        return None
    
    # Look for number patterns: "100", "100.5", "0.01"
    # Optionally followed by token symbol
    amount_match = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:USDC|USDT|ETH|BTC|DAI|MNEE|WETH|MATIC|ARB|OP)?',
        text,
        re.IGNORECASE
    )
    if amount_match:
        return amount_match.group(1)
    
    return None


def extract_token(text: str) -> Optional[str]:
    """
    Extract a token symbol from text.
    
    Searches for known token symbols in the text (case-insensitive).
    Returns the first match.
    
    Args:
        text: Text to search
        
    Returns:
        Token symbol in uppercase, or None if not found
    """
    if not text:
        return None
    
    # List of known tokens - should match token_registry
    known_tokens = [
        'USDC', 'USDT', 'ETH', 'BTC', 'DAI', 'MNEE', 
        'WETH', 'MATIC', 'ARB', 'OP', 'AVAX'
    ]
    
    text_lower = text.lower()
    for token in known_tokens:
        if token.lower() in text_lower:
            return token
    
    return None


def extract_chain(text: str) -> Optional[int]:
    """
    Extract a blockchain chain ID from text.
    
    Recognizes common chain names and returns their chain IDs.
    
    Args:
        text: Text to search
        
    Returns:
        Chain ID (e.g., 8453 for Base), or None if not found
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Map of chain names to chain IDs
    chain_mapping = {
        'ethereum': 1,
        'mainnet': 1,
        'eth-mainnet': 1,
        'polygon': 137,
        'matic': 137,
        'arbitrum': 42161,
        'arb': 42161,
        'arbitrum one': 42161,
        'optimism': 10,
        'opt': 10,
        'optimistic': 10,
        'base': 8453,
        'base mainnet': 8453,
        'bsc': 56,
        'binance': 56,
        'binance smart chain': 56,
        'avalanche': 43114,
        'avax': 43114,
        'cronos': 25,
        'cro': 25,
    }
    
    for chain_name, chain_id in chain_mapping.items():
        if chain_name in text_lower:
            return chain_id
    
    return None
