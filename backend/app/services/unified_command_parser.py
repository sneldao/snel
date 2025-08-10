"""
Unified command parser for consistent command detection and parsing.
Enhanced with intelligent pattern matching and performance optimization.
"""
import re
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal

from app.models.unified_models import (
    CommandType, UnifiedCommand, CommandDetails, TokenInfo, ValidationResult
)
from app.services.enhanced_command_patterns import enhanced_patterns

logger = logging.getLogger(__name__)


class UnifiedCommandParser:
    """
    Unified parser for all command types with intelligent pattern matching.
    Optimized for performance, maintainability, and user experience.
    """
    
    @classmethod
    def detect_command_type(cls, command: str) -> CommandType:
        """
        Detect the type of command using enhanced pattern system.
        Optimized for performance with intelligent priority-based matching.
        """
        command_type, extracted_params = enhanced_patterns.detect_command_type(command)
        return command_type
    
    @classmethod
    def detect_command_with_params(cls, command: str) -> tuple[CommandType, Optional[Dict]]:
        """
        Detect command type and extract parameters in one operation.
        More efficient for complex parsing operations.
        """
        return enhanced_patterns.detect_command_type(command)
    
    @classmethod
    def parse_command(cls, command: str, command_type: CommandType) -> Optional[CommandDetails]:
        """Parse command details based on the detected type."""
        command_clean = command.lower().strip()
        
        try:
            if command_type == CommandType.TRANSFER:
                return cls._parse_transfer(command_clean)
            elif command_type == CommandType.BRIDGE:
                return cls._parse_bridge(command_clean)
            elif command_type == CommandType.SWAP:
                return cls._parse_swap(command_clean)
            elif command_type == CommandType.BALANCE:
                return cls._parse_balance(command_clean)
            elif command_type == CommandType.PORTFOLIO:
                return cls._parse_portfolio(command_clean)
            elif command_type == CommandType.PROTOCOL_RESEARCH:
                return cls._parse_protocol_research(command_clean)
            elif command_type == CommandType.CONFIRMATION:
                return cls._parse_confirmation(command_clean)
            else:
                return None
                
        except Exception as e:
            logger.exception(f"Error parsing command: {command}")
            return None
    
    @classmethod
    def _parse_transfer(cls, command: str) -> Optional[CommandDetails]:
        """Parse transfer command details."""
        # Use the enhanced patterns to detect and extract parameters
        command_type, extracted_params = enhanced_patterns.detect_command_type(command)
        
        if command_type == CommandType.TRANSFER and extracted_params:
            return CommandDetails(
                amount=float(extracted_params["amount"]),
                token_in=TokenInfo(symbol=extracted_params["token"].upper()),
                destination=extracted_params["destination"]
            )
        return None
    
    @classmethod
    def _parse_bridge(cls, command: str) -> Optional[CommandDetails]:
        """Parse bridge command details."""
        # Use the enhanced patterns to detect and extract parameters
        command_type, extracted_params = enhanced_patterns.detect_command_type(command)
        
        if command_type == CommandType.BRIDGE and extracted_params:
            return CommandDetails(
                amount=float(extracted_params["amount"]),
                token_in=TokenInfo(symbol=extracted_params["token"].upper()),
                source_chain=extracted_params.get("source_chain"),
                destination_chain=extracted_params["dest_chain"]
            )
        return None
    
    @classmethod
    def _parse_swap(cls, command: str) -> Optional[CommandDetails]:
        """Parse swap command details."""
        # Use the enhanced patterns to detect and extract parameters
        command_type, extracted_params = enhanced_patterns.detect_command_type(command)
        
        if command_type in [CommandType.SWAP, CommandType.CROSS_CHAIN_SWAP] and extracted_params:
            # Handle USD amount vs token amount
            if "usd_amount" in extracted_params and extracted_params["usd_amount"]:
                amount = float(extracted_params["usd_amount"])
                additional_params = {"is_usd_amount": True}
            else:
                amount = float(extracted_params["amount"])
                additional_params = {"is_usd_amount": False}
            
            return CommandDetails(
                amount=amount,
                token_in=TokenInfo(symbol=extracted_params["token_in"].upper()),
                token_out=TokenInfo(symbol=extracted_params["token_out"].upper()),
                additional_params=additional_params
            )
        return None
    
    @classmethod
    def _parse_balance(cls, command: str) -> Optional[CommandDetails]:
        """Parse balance command details."""
        # Use the enhanced patterns to detect and extract parameters
        command_type, extracted_params = enhanced_patterns.detect_command_type(command)
        
        if command_type == CommandType.BALANCE and extracted_params:
            token = extracted_params.get("token")
            return CommandDetails(
                token_in=TokenInfo(symbol=token.upper()) if token else None
            )
        return CommandDetails()  # Balance commands can work without specific token
    
    @classmethod
    def _parse_portfolio(cls, command: str) -> Optional[CommandDetails]:
        """Parse portfolio command details."""
        # Portfolio commands don't need specific parsing
        return CommandDetails()
    
    @classmethod
    def _parse_protocol_research(cls, command: str) -> Optional[CommandDetails]:
        """Parse protocol research command details."""
        # Use the enhanced patterns to detect and extract parameters
        command_type, extracted_params = enhanced_patterns.detect_command_type(command)
        
        if command_type == CommandType.PROTOCOL_RESEARCH and extracted_params:
            protocol = extracted_params.get("protocol")
            return CommandDetails(
                protocol=protocol,
                additional_params={"research_type": "protocol"}
            )
        return None
    
    @classmethod
    def _parse_confirmation(cls, command: str) -> Optional[CommandDetails]:
        """Parse confirmation command details."""
        positive_confirmations = ["yes", "confirm", "proceed", "continue"]
        negative_confirmations = ["no", "cancel", "abort", "stop"]
        
        command_clean = command.lower().strip()
        
        if command_clean in positive_confirmations:
            return CommandDetails(additional_params={"confirmation": True})
        elif command_clean in negative_confirmations:
            return CommandDetails(additional_params={"confirmation": False})
        
        return None
    
    @classmethod
    def validate_command(cls, unified_command: UnifiedCommand) -> ValidationResult:
        """Validate a unified command for completeness and requirements."""
        missing_requirements = []
        
        # Check wallet requirements for transaction commands
        transaction_commands = [CommandType.TRANSFER, CommandType.BRIDGE, CommandType.SWAP]
        if unified_command.command_type in transaction_commands:
            if not unified_command.wallet_address:
                missing_requirements.append("wallet_address")
            if not unified_command.chain_id:
                missing_requirements.append("chain_id")
        
        # Check command-specific requirements
        if unified_command.command_type == CommandType.TRANSFER:
            if not unified_command.details or not unified_command.details.amount:
                missing_requirements.append("transfer_amount")
            if not unified_command.details or not unified_command.details.destination:
                missing_requirements.append("destination_address")
        
        elif unified_command.command_type == CommandType.BRIDGE:
            if not unified_command.details or not unified_command.details.amount:
                missing_requirements.append("bridge_amount")
            if not unified_command.details or not unified_command.details.destination_chain:
                missing_requirements.append("destination_chain")
        
        elif unified_command.command_type == CommandType.SWAP:
            if not unified_command.details or not unified_command.details.amount:
                missing_requirements.append("swap_amount")
            if not unified_command.details or not unified_command.details.token_out:
                missing_requirements.append("output_token")
        
        # Portfolio and balance commands need wallet for meaningful results
        if unified_command.command_type in [CommandType.PORTFOLIO, CommandType.BALANCE]:
            if not unified_command.wallet_address:
                missing_requirements.append("wallet_address")
        
        is_valid = len(missing_requirements) == 0
        error_message = None
        
        if not is_valid:
            if "wallet_address" in missing_requirements:
                error_message = "Please connect your wallet to perform this operation."
            elif "chain_id" in missing_requirements:
                error_message = "Please connect to a supported network."
            else:
                error_message = f"Missing required information: {', '.join(missing_requirements)}"
        
        return ValidationResult(
            is_valid=is_valid,
            error_message=error_message,
            missing_requirements=missing_requirements
        )
    
    @classmethod
    def create_unified_command(
        cls,
        command: str,
        wallet_address: Optional[str] = None,
        chain_id: Optional[int] = None,
        user_name: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ) -> UnifiedCommand:
        """Create a unified command from input parameters."""
        command_type = cls.detect_command_type(command)
        details = cls.parse_command(command, command_type)
        
        return UnifiedCommand(
            command=command,
            command_type=command_type,
            wallet_address=wallet_address,
            chain_id=chain_id,
            user_name=user_name,
            openai_api_key=openai_api_key,
            details=details
        )
