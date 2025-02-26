import logging
import traceback
from typing import Dict, Any, Optional, Type, Callable, TypeVar, Union
from fastapi import HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar('T')
R = TypeVar('R')

class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "error": "Failed to process swap request",
                "error_code": "SWAP_FAILED",
                "details": {
                    "token_in": "ETH",
                    "token_out": "USDC",
                    "reason": "Insufficient liquidity"
                }
            }
        }

# Error codes
class ErrorCode:
    # General errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    
    # Token errors
    TOKEN_NOT_FOUND = "TOKEN_NOT_FOUND"
    INVALID_TOKEN = "INVALID_TOKEN"
    
    # Swap errors
    SWAP_FAILED = "SWAP_FAILED"
    NO_ROUTE_FOUND = "NO_ROUTE_FOUND"
    INSUFFICIENT_LIQUIDITY = "INSUFFICIENT_LIQUIDITY"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    INSUFFICIENT_ALLOWANCE = "INSUFFICIENT_ALLOWANCE"
    
    # Chain errors
    UNSUPPORTED_CHAIN = "UNSUPPORTED_CHAIN"
    
    # Transaction errors
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    BUILD_TRANSACTION_FAILED = "BUILD_TRANSACTION_FAILED"

# Error mapping from exception types to HTTP status codes and error codes
ERROR_MAPPING = {
    ValueError: (status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR),
    KeyError: (status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR),
    TypeError: (status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR),
    
    # Custom exceptions from kyber.py
    "KyberSwapError": (status.HTTP_400_BAD_REQUEST, ErrorCode.SWAP_FAILED),
    "NoRouteFoundError": (status.HTTP_400_BAD_REQUEST, ErrorCode.NO_ROUTE_FOUND),
    "InsufficientLiquidityError": (status.HTTP_400_BAD_REQUEST, ErrorCode.INSUFFICIENT_LIQUIDITY),
    "InvalidTokenError": (status.HTTP_400_BAD_REQUEST, ErrorCode.INVALID_TOKEN),
    "BuildTransactionError": (status.HTTP_400_BAD_REQUEST, ErrorCode.BUILD_TRANSACTION_FAILED),
    "TransferFromFailedError": (status.HTTP_400_BAD_REQUEST, ErrorCode.INSUFFICIENT_ALLOWANCE),
}

def get_error_details(exception: Exception) -> Dict[str, Any]:
    """Extract useful details from an exception."""
    details = {
        "exception_type": exception.__class__.__name__,
    }
    
    # Add exception args if available
    if exception.args:
        details["message"] = str(exception)
    
    # Add custom attributes if available
    for attr in dir(exception):
        if not attr.startswith('_') and attr not in ('args', 'with_traceback'):
            try:
                value = getattr(exception, attr)
                if not callable(value):
                    details[attr] = str(value)
            except Exception:
                pass
    
    return details

def handle_exception(exception: Exception) -> HTTPException:
    """
    Convert any exception to a standardized HTTPException.
    
    Args:
        exception: The exception to handle
        
    Returns:
        An HTTPException with standardized format
    """
    # Get exception class name for lookup
    exception_class_name = exception.__class__.__name__
    
    # Look up status code and error code
    status_code, error_code = ERROR_MAPPING.get(
        exception.__class__,
        ERROR_MAPPING.get(
            exception_class_name,
            (status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_ERROR)
        )
    )
    
    # Get error message
    error_message = str(exception)
    
    # Log the error with traceback for server-side debugging
    logger.error(
        f"Error {error_code} ({status_code}): {error_message}",
        exc_info=True
    )
    
    # Create error response
    error_response = ErrorResponse(
        error=error_message,
        error_code=error_code,
        details=get_error_details(exception)
    )
    
    # Return HTTPException
    return HTTPException(
        status_code=status_code,
        detail=error_response.dict()
    )

def safe_execute(func: Callable[..., R], *args, **kwargs) -> Union[R, ErrorResponse]:
    """
    Execute a function safely, catching and standardizing any exceptions.
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Either the function result or an ErrorResponse
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {str(e)}", exc_info=True)
        
        # Get exception class name for lookup
        exception_class_name = e.__class__.__name__
        
        # Look up error code
        _, error_code = ERROR_MAPPING.get(
            e.__class__,
            ERROR_MAPPING.get(
                exception_class_name,
                (status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_ERROR)
            )
        )
        
        return ErrorResponse(
            error=str(e),
            error_code=error_code,
            details=get_error_details(e)
        )

async def safe_execute_async(func: Callable[..., R], *args, **kwargs) -> Union[R, ErrorResponse]:
    """
    Execute an async function safely, catching and standardizing any exceptions.
    
    Args:
        func: The async function to execute
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Either the function result or an ErrorResponse
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {str(e)}", exc_info=True)
        
        # Get exception class name for lookup
        exception_class_name = e.__class__.__name__
        
        # Look up error code
        _, error_code = ERROR_MAPPING.get(
            e.__class__,
            ERROR_MAPPING.get(
                exception_class_name,
                (status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_ERROR)
            )
        )
        
        return ErrorResponse(
            error=str(e),
            error_code=error_code,
            details=get_error_details(e)
        ) 