from decimal import Decimal, ROUND_DOWN
import logging

logger = logging.getLogger(__name__)

def amount_to_smallest_units(amount: float, decimals: int) -> int:
    """
    Convert a decimal amount to the smallest units based on token decimals.
    This is a safer, more reliable implementation that avoids floating point errors.
    
    Args:
        amount: The token amount as a float (e.g., 1.5 ETH)
        decimals: The number of decimals for the token (e.g., 18 for ETH)
        
    Returns:
        The amount in smallest units (e.g., wei for ETH)
    """
    try:
        # Convert to string first to preserve precision, then to Decimal
        amount_decimal = Decimal(str(amount))
        
        # Calculate the scaling factor (10^decimals)
        factor = Decimal(10) ** decimals
        
        # Multiply by the scaling factor
        amount_in_smallest = amount_decimal * factor
        
        # Round down to ensure we don't exceed the user's intended amount
        result = int(amount_in_smallest.quantize(Decimal('1.'), rounding=ROUND_DOWN))
        
        # Safety check for unreasonably large values
        if result > 10**36:  # This is an extremely large number (much larger than all ETH in existence)
            logger.error(f"SAFETY LIMIT EXCEEDED: Conversion result too large: {result}")
            raise ValueError(f"Conversion result implausibly large: {result} (from {amount} with {decimals} decimals)")
            
        logger.info(f"Converted {amount} to {result} (smallest units with {decimals} decimals)")
        return result
        
    except Exception as e:
        logger.error(f"Error converting {amount} to smallest units: {e}")
        raise

def smallest_units_to_amount(amount_in_smallest: int, decimals: int) -> float:
    """
    Convert an amount in smallest units back to a decimal value.
    
    Args:
        amount_in_smallest: The amount in smallest units (e.g., wei for ETH)
        decimals: The number of decimals for the token (e.g., 18 for ETH)
        
    Returns:
        The amount as a human-readable float (e.g., ETH)
    """
    try:
        # Convert to Decimal for precise calculation
        amount_decimal = Decimal(amount_in_smallest)
        
        # Calculate the scaling factor (10^decimals)
        factor = Decimal(10) ** decimals
        
        # Divide by the scaling factor
        result = amount_decimal / factor
        
        # Convert to float for easier use in the application
        result_float = float(result)
        
        logger.info(f"Converted {amount_in_smallest} (smallest units) to {result_float} (with {decimals} decimals)")
        return result_float
        
    except Exception as e:
        logger.error(f"Error converting {amount_in_smallest} smallest units to amount: {e}")
        raise

def format_token_amount(amount: float, decimals: int = 18, max_decimals: int = 6) -> str:
    """
    Format a token amount for human-readable display.
    
    Args:
        amount: The token amount to format
        decimals: The token's decimal places
        max_decimals: Maximum number of decimal places to show
        
    Returns:
        A formatted string representation of the amount
    """
    # If amount is very small, use scientific notation
    if 0 < amount < 0.000001:
        return f"{amount:.8e}"
        
    # For normal values, format with appropriate decimal places
    decimal_places = min(max_decimals, decimals)
    format_str = f"{{:.{decimal_places}f}}"
    return format_str.format(amount) 