"""
Centralized error handling framework for SNEL.

This module provides standardized error types and handling patterns
to replace the mock returns and placeholder implementations throughout
the codebase.

Core Principles:
- FAIL FAST: Clear, immediate error responses instead of mock data
- STRUCTURED: Consistent error format across all services
- ACTIONABLE: Errors include enough context for debugging and recovery
- MONITORED: All errors are logged with appropriate severity levels
"""

import logging
import traceback
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for monitoring and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification and routing."""
    CONFIGURATION = "configuration"
    NETWORK = "network"
    PROTOCOL = "protocol"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    SLIPPAGE = "slippage"
    TIMEOUT = "timeout"
    INTERNAL = "internal"


@dataclass
class ErrorContext:
    """Additional context for error analysis."""
    user_id: Optional[str] = None
    chain_id: Optional[int] = None
    token_symbol: Optional[str] = None
    protocol: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


class SNELError(Exception):
    """
    Base exception class for all SNEL-related errors.

    Provides structured error information for consistent
    handling and monitoring across the application.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None,
        suggested_action: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext()
        self.cause = cause
        self.user_message = user_message or "An error occurred while processing your request."
        self.suggested_action = suggested_action
        self.retry_after = retry_after
        self.timestamp = datetime.utcnow()

        super().__init__(message)

        # Log error immediately
        self._log_error()

    def _log_error(self):
        """Log error with appropriate severity level."""
        # NB: do not include a "message" key here (LogRecord.message is reserved)
        log_data = {
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context.__dict__ if self.context else {},
            "error_timestamp": self.timestamp.isoformat()
        }

        if self.cause:
            log_data["cause"] = str(self.cause)

        log_message = f"[{self.error_code}] {self.message}"

        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=log_data)
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=log_data)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=log_data)
        else:
            logger.info(log_message, extra=log_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "suggested_action": self.suggested_action,
            "retry_after": self.retry_after,
            "context": {
                "chain_id": self.context.chain_id,
                "protocol": self.context.protocol,
                "request_id": self.context.request_id
            } if self.context else {}
        }


# Configuration Errors
class ConfigurationError(SNELError):
    """Errors related to system configuration."""

    def __init__(self, message: str, config_key: str, **kwargs):
        super().__init__(
            message=message,
            error_code=f"CONFIG_{config_key.upper()}_ERROR",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            suggested_action="Check system configuration and restart if necessary",
            **kwargs
        )


class InvalidTokenConfigError(ConfigurationError):
    """Token configuration is invalid or missing."""

    def __init__(self, token_symbol: str, chain_id: int, **kwargs):
        context = ErrorContext(token_symbol=token_symbol, chain_id=chain_id)
        super().__init__(
            message=f"Invalid token configuration for {token_symbol} on chain {chain_id}",
            config_key="token",
            context=context,
            user_message=f"Token {token_symbol} is not supported on this network",
            **kwargs
        )


class InvalidChainConfigError(ConfigurationError):
    """Chain configuration is invalid or missing."""

    def __init__(self, chain_id: int, **kwargs):
        context = ErrorContext(chain_id=chain_id)
        super().__init__(
            message=f"Invalid chain configuration for chain {chain_id}",
            config_key="chain",
            context=context,
            user_message=f"Network {chain_id} is not supported",
            **kwargs
        )


class MissingAPIKeyError(ConfigurationError):
    """Required API key is missing."""

    def __init__(self, service: str, **kwargs):
        super().__init__(
            message=f"Missing API key for {service}",
            config_key="api_key",
            user_message="Service temporarily unavailable due to configuration issues",
            suggested_action=f"Set {service.upper()}_API_KEY environment variable",
            **kwargs
        )


# Network Errors
class NetworkError(SNELError):
    """Network-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            user_message="Network connectivity issue. Please try again.",
            suggested_action="Retry request after a short delay",
            retry_after=30,
            **kwargs
        )


class RPCConnectionError(NetworkError):
    """RPC endpoint connection failed."""

    def __init__(self, rpc_url: str, chain_id: int, **kwargs):
        context = ErrorContext(chain_id=chain_id, additional_data={"rpc_url": rpc_url})
        super().__init__(
            message=f"Failed to connect to RPC endpoint {rpc_url} for chain {chain_id}",
            context=context,
            user_message=f"Network {chain_id} is temporarily unavailable",
            **kwargs
        )


class ProtocolAPIError(NetworkError):
    """Protocol API request failed."""

    def __init__(self, protocol: str, endpoint: str, status_code: int, **kwargs):
        context = ErrorContext(protocol=protocol, additional_data={
            "endpoint": endpoint,
            "status_code": status_code
        })
        super().__init__(
            message=f"{protocol} API request failed: {endpoint} returned {status_code}",
            context=context,
            user_message=f"{protocol} service is temporarily unavailable",
            **kwargs
        )


# Protocol Errors
class ProtocolError(SNELError):
    """Protocol-specific errors."""

    def __init__(self, message: str, protocol: str, **kwargs):
        context = ErrorContext(protocol=protocol)
        super().__init__(
            message=message,
            error_code=f"{protocol.upper()}_ERROR",
            category=ErrorCategory.PROTOCOL,
            context=context,
            **kwargs
        )


class ProtocolNotSupportedError(ProtocolError):
    """Protocol is not supported on the specified chain."""

    def __init__(self, protocol: str, chain_id: int, **kwargs):
        context = ErrorContext(protocol=protocol, chain_id=chain_id)
        super().__init__(
            message=f"Protocol {protocol} is not supported on chain {chain_id}",
            protocol=protocol,
            context=context,
            user_message=f"{protocol} is not available on this network",
            suggested_action="Try a different protocol or network",
            **kwargs
        )


class InsufficientLiquidityError(ProtocolError):
    """Insufficient liquidity for the requested trade."""

    def __init__(self, protocol: str, token_pair: str, amount: str, **kwargs):
        super().__init__(
            message=f"Insufficient liquidity on {protocol} for {amount} {token_pair}",
            protocol=protocol,
            user_message="Insufficient liquidity for this trade size",
            suggested_action="Try a smaller amount or different token pair",
            **kwargs
        )


class SlippageExceededError(ProtocolError):
    """Trade would exceed maximum allowed slippage."""

    def __init__(self, protocol: str, expected_slippage: float, max_slippage: float, **kwargs):
        super().__init__(
            message=f"Slippage {expected_slippage}% exceeds maximum {max_slippage}%",
            protocol=protocol,
            category=ErrorCategory.SLIPPAGE,
            user_message=f"Price slippage ({expected_slippage:.2f}%) exceeds your limit ({max_slippage:.2f}%)",
            suggested_action="Increase slippage tolerance or try a smaller amount",
            **kwargs
        )


# Validation Errors
class ValidationError(SNELError):
    """Input validation errors."""

    def __init__(self, message: str, field: str, value: Any, **kwargs):
        context = ErrorContext(additional_data={"field": field, "value": str(value)})
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            context=context,
            user_message=f"Invalid {field}: {message}",
            **kwargs
        )


class InvalidAmountError(ValidationError):
    """Invalid trade amount."""

    def __init__(self, amount: str, reason: str, **kwargs):
        super().__init__(
            message=f"Invalid amount {amount}: {reason}",
            field="amount",
            value=amount,
            user_message=f"Invalid amount: {reason}",
            **kwargs
        )


class InvalidAddressError(ValidationError):
    """Invalid wallet or contract address."""

    def __init__(self, address: str, **kwargs):
        super().__init__(
            message=f"Invalid address format: {address}",
            field="address",
            value=address,
            user_message="Invalid wallet address format",
            **kwargs
        )


# Rate Limiting Errors
class RateLimitError(SNELError):
    """Rate limiting errors."""

    def __init__(self, service: str, limit: int, reset_time: int, **kwargs):
        super().__init__(
            message=f"Rate limit exceeded for {service}: {limit} requests",
            error_code="RATE_LIMIT_EXCEEDED",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            user_message="Too many requests. Please wait before trying again.",
            suggested_action=f"Wait {reset_time} seconds before retrying",
            retry_after=reset_time,
            **kwargs
        )


# Authentication Errors
class AuthenticationError(SNELError):
    """Authentication-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            user_message="Authentication failed",
            suggested_action="Check your API credentials",
            **kwargs
        )


# Timeout Errors
class TimeoutError(SNELError):
    """Request timeout errors."""

    def __init__(self, operation: str, timeout_seconds: int, **kwargs):
        super().__init__(
            message=f"Operation {operation} timed out after {timeout_seconds} seconds",
            error_code="TIMEOUT_ERROR",
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            user_message="Request timed out. Please try again.",
            suggested_action="Retry with a longer timeout or check network connectivity",
            retry_after=60,
            **kwargs
        )


# Insufficient Funds Errors
class InsufficientFundsError(SNELError):
    """Insufficient funds for transaction."""

    def __init__(self, required: str, available: str, token: str, **kwargs):
        context = ErrorContext(token_symbol=token, additional_data={
            "required": required,
            "available": available
        })
        super().__init__(
            message=f"Insufficient {token} balance: need {required}, have {available}",
            error_code="INSUFFICIENT_FUNDS",
            category=ErrorCategory.INSUFFICIENT_FUNDS,
            severity=ErrorSeverity.LOW,
            context=context,
            user_message=f"Insufficient {token} balance",
            suggested_action="Add more funds to your wallet",
            **kwargs
        )


# Error Handler Decorators
def handle_errors(default_error_message: str = "An unexpected error occurred"):
    """
    Decorator to handle errors in service methods.

    Converts unhandled exceptions to SNELError instances
    for consistent error handling across the application.
    """
    def decorator(func):
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SNELError:
                # Re-raise SNEL errors as-is
                raise
            except Exception as e:
                # Convert other exceptions to SNELError
                logger.error(f"Unhandled error in {func.__name__}: {e}")
                raise SNELError(
                    message=f"Unhandled error in {func.__name__}: {str(e)}",
                    error_code="UNHANDLED_ERROR",
                    category=ErrorCategory.INTERNAL,
                    severity=ErrorSeverity.HIGH,
                    cause=e,
                    user_message=default_error_message,
                    suggested_action="Please try again or contact support if the issue persists"
                )

        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except SNELError:
                # Re-raise SNEL errors as-is
                raise
            except Exception as e:
                # Convert other exceptions to SNELError
                logger.error(f"Unhandled error in {func.__name__}: {e}")
                raise SNELError(
                    message=f"Unhandled error in {func.__name__}: {str(e)}",
                    error_code="UNHANDLED_ERROR",
                    category=ErrorCategory.INTERNAL,
                    severity=ErrorSeverity.HIGH,
                    cause=e,
                    user_message=default_error_message,
                    suggested_action="Please try again or contact support if the issue persists"
                )

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Circuit Breaker Pattern
class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    Temporarily disables failing services to allow recovery
    and prevent resource exhaustion.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise SNELError(
                        message=f"Circuit breaker {self.name} is OPEN",
                        error_code="CIRCUIT_BREAKER_OPEN",
                        category=ErrorCategory.INTERNAL,
                        severity=ErrorSeverity.HIGH,
                        user_message="Service is temporarily unavailable",
                        suggested_action=f"Try again in {self.recovery_timeout} seconds",
                        retry_after=self.recovery_timeout
                    )

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True

        return (datetime.utcnow() - self.last_failure_time).total_seconds() > self.recovery_timeout

    def _on_success(self):
        """Reset circuit breaker on successful call."""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """Handle failure and potentially open circuit breaker."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker {self.name} opened after {self.failure_count} failures")


# Global error registry for monitoring
error_registry: Dict[str, List[SNELError]] = {}

def register_error(error: SNELError):
    """Register error for monitoring and analytics."""
    error_code = error.error_code
    if error_code not in error_registry:
        error_registry[error_code] = []

    error_registry[error_code].append(error)

    # Keep only recent errors (last 1000 per type)
    if len(error_registry[error_code]) > 1000:
        error_registry[error_code] = error_registry[error_code][-1000:]

def get_error_stats() -> Dict[str, Any]:
    """Get error statistics for monitoring."""
    stats = {}
    for error_code, errors in error_registry.items():
        recent_errors = [e for e in errors
                        if (datetime.utcnow() - e.timestamp).total_seconds() < 3600]

        stats[error_code] = {
            "total_count": len(errors),
            "recent_count": len(recent_errors),
            "last_occurrence": max(e.timestamp for e in errors).isoformat() if errors else None,
            "severity_breakdown": {
                severity.value: len([e for e in recent_errors if e.severity == severity])
                for severity in ErrorSeverity
            }
        }

    return stats
