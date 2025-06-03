"""
Centralized exception handling for SNEL backend.
Provides consistent error responses and proper error categorization.
"""
from typing import Any, Dict, Optional, List
from enum import Enum


class ErrorCode(str, Enum):
    """Standardized error codes for consistent error handling."""
    
    # Validation Errors (4xx)
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_AMOUNT = "INVALID_AMOUNT"
    INVALID_ADDRESS = "INVALID_ADDRESS"
    INVALID_TOKEN = "INVALID_TOKEN"
    INVALID_CHAIN = "INVALID_CHAIN"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    
    # Authentication/Authorization Errors (4xx)
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_API_KEY = "INVALID_API_KEY"
    RATE_LIMITED = "RATE_LIMITED"
    
    # Business Logic Errors (4xx)
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    COMMAND_PARSE_ERROR = "COMMAND_PARSE_ERROR"
    WALLET_NOT_CONNECTED = "WALLET_NOT_CONNECTED"
    CHAIN_NOT_SUPPORTED = "CHAIN_NOT_SUPPORTED"
    
    # External Service Errors (5xx)
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    BRIAN_API_ERROR = "BRIAN_API_ERROR"
    EXA_API_ERROR = "EXA_API_ERROR"
    FIRECRAWL_API_ERROR = "FIRECRAWL_API_ERROR"
    BLOCKCHAIN_RPC_ERROR = "BLOCKCHAIN_RPC_ERROR"
    
    # Internal Server Errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class SNELException(Exception):
    """Base exception class for all SNEL-specific errors."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.suggestions = suggestions or []
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": {
                "message": self.message,
                "code": self.code.value,
                "details": self.details,
                "suggestions": self.suggestions
            }
        }


class ValidationError(SNELException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INVALID_INPUT,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        suggestions: Optional[List[str]] = None
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["provided_value"] = str(value)
        
        super().__init__(
            message=message,
            code=code,
            status_code=400,
            details=details,
            suggestions=suggestions
        )


class BusinessLogicError(SNELException):
    """Raised when business logic constraints are violated."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode,
        suggestions: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=400,
            details=details,
            suggestions=suggestions
        )


class ExternalServiceError(SNELException):
    """Raised when external service calls fail."""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        code: ErrorCode = ErrorCode.EXTERNAL_SERVICE_ERROR,
        original_error: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        details = {"service": service_name}
        if original_error:
            details["original_error"] = original_error
        if retry_after:
            details["retry_after_seconds"] = retry_after
        
        suggestions = []
        if retry_after:
            suggestions.append(f"Please try again in {retry_after} seconds")
        else:
            suggestions.append("Please try again later")
        
        super().__init__(
            message=message,
            code=code,
            status_code=503,
            details=details,
            suggestions=suggestions
        )


class ConfigurationError(SNELException):
    """Raised when configuration is invalid or missing."""
    
    def __init__(
        self,
        message: str,
        setting_name: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ):
        details = {}
        if setting_name:
            details["setting"] = setting_name
        
        super().__init__(
            message=message,
            code=ErrorCode.CONFIGURATION_ERROR,
            status_code=500,
            details=details,
            suggestions=suggestions or ["Check your environment configuration"]
        )


class AuthenticationError(SNELException):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication required",
        code: ErrorCode = ErrorCode.UNAUTHORIZED
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=401,
            suggestions=["Please provide valid authentication credentials"]
        )


class RateLimitError(SNELException):
    """Raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
        limit: Optional[int] = None
    ):
        details = {"retry_after_seconds": retry_after}
        if limit:
            details["rate_limit"] = limit
        
        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMITED,
            status_code=429,
            details=details,
            suggestions=[f"Please wait {retry_after} seconds before trying again"]
        )


# Convenience functions for common error scenarios
def command_parse_error(command: str, expected_format: str) -> ValidationError:
    """Create a standardized command parsing error."""
    return ValidationError(
        message=f"Could not parse command: '{command}'",
        code=ErrorCode.COMMAND_PARSE_ERROR,
        field="command",
        value=command,
        suggestions=[f"Expected format: {expected_format}"]
    )


def invalid_amount_error(amount: Any, min_amount: float = 0) -> ValidationError:
    """Create a standardized invalid amount error."""
    return ValidationError(
        message=f"Invalid amount: {amount}",
        code=ErrorCode.INVALID_AMOUNT,
        field="amount",
        value=amount,
        suggestions=[f"Amount must be greater than {min_amount}"]
    )


def invalid_address_error(address: str) -> ValidationError:
    """Create a standardized invalid address error."""
    return ValidationError(
        message=f"Invalid address or ENS name: {address}",
        code=ErrorCode.INVALID_ADDRESS,
        field="address",
        value=address,
        suggestions=[
            "Provide a valid Ethereum address (0x...)",
            "Provide a valid ENS name (name.eth)"
        ]
    )


def unsupported_chain_error(chain_id: int, supported_chains: List[int]) -> ValidationError:
    """Create a standardized unsupported chain error."""
    return ValidationError(
        message=f"Chain ID {chain_id} is not supported",
        code=ErrorCode.CHAIN_NOT_SUPPORTED,
        field="chain_id",
        value=chain_id,
        suggestions=[f"Supported chains: {', '.join(map(str, supported_chains))}"]
    )


def wallet_not_connected_error() -> BusinessLogicError:
    """Create a standardized wallet not connected error."""
    return BusinessLogicError(
        message="Wallet not connected",
        code=ErrorCode.WALLET_NOT_CONNECTED,
        suggestions=["Please connect your wallet to perform this operation"]
    )


def external_service_timeout_error(service_name: str, timeout: int) -> ExternalServiceError:
    """Create a standardized external service timeout error."""
    return ExternalServiceError(
        message=f"{service_name} service timed out after {timeout} seconds",
        service_name=service_name,
        retry_after=30
    )
