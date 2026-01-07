"""
Unified Parser - Single Source of Truth for Command Parsing
Consolidated from multiple parsing implementations following DRY principles.
Enhanced with intelligent amount parsing and comprehensive validation.
"""
import re
import logging
from typing import Dict, List, Tuple, Optional, Any, NamedTuple
from enum import Enum
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass

from app.models.unified_models import (
    CommandType, UnifiedCommand, CommandDetails, TokenInfo, ValidationResult
)

logger = logging.getLogger(__name__)


class AmountType(Enum):
    """Types of amounts that can be parsed."""
    TOKEN_AMOUNT = "token_amount"  # e.g., "1 ETH", "$1 of ETH"
    USD_AMOUNT = "usd_amount"      # e.g., "$1 worth of ETH", "1 dollar worth of ETH"


@dataclass
class ParsedAmount:
    """Structured representation of parsed amount."""
    value: Decimal
    amount_type: AmountType
    token_symbol: str
    original_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": float(self.value),
            "amount_type": self.amount_type.value,
            "token_symbol": self.token_symbol,
            "original_text": self.original_text
        }


class UnifiedParser:
    """
    Single consolidated parser following CLEAN, MODULAR, and DRY principles.
    Handles all command parsing with intelligent amount detection and validation.
    """

    def __init__(self):
        """Initialize with compiled patterns for performance."""
        self._patterns = self._build_patterns()
        self._pattern_cache = {}

    def _build_patterns(self) -> Dict[CommandType, List[Dict[str, Any]]]:
        """Build comprehensive pattern hierarchy with clear priorities."""

        # Note: Order matters! More specific patterns (like BRIDGE_TO_PRIVACY) should come before generic ones (BRIDGE)
        return {
            # Contextual questions should come early to catch natural language queries
            CommandType.CONTEXTUAL_QUESTION: [
                {
                    "pattern": re.compile(
                        r"(?:talk|tell|teach|explain|help|guide|how|show|walk|describe)\s+(?:me\s+)?(?:through|about)?",
                        re.IGNORECASE
                    ),
                    "description": "Natural language guide/explanation request",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"(?:can you help|could you help|how do i|how can i|show me|teach me)\s+",
                        re.IGNORECASE
                    ),
                    "description": "Help/how-to request",
                    "priority": 2
                }
            ],
            # Privacy bridges must be checked before generic bridges
            CommandType.SET_PRIVACY_DEFAULT: [
                {
                    "pattern": re.compile(
                        r"set\s+(?:my\s+)?(?:default\s+)?privacy\s+(?:to\s+)?(?P<privacy_level>public|private|compliance)",
                        re.IGNORECASE
                    ),
                    "description": "Set default privacy level",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"(?:make|set)\s+all\s+my\s+transactions\s+(?P<privacy_level>public|private|compliance)",
                        re.IGNORECASE
                    ),
                    "description": "Set global privacy preference",
                    "priority": 2
                }
            ],
            CommandType.OVERRIDE_PRIVACY: [
                {
                    "pattern": re.compile(
                        r"(?:send|make|keep)\s+this\s+transaction\s+(?P<privacy_level>public|private|compliance)",
                        re.IGNORECASE
                    ),
                    "description": "Override privacy for specific transaction",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"(?:use|with)\s+(?P<privacy_level>public|private|compliance)\s+(?:settlement|transaction|privacy)",
                        re.IGNORECASE
                    ),
                    "description": "Explicit privacy override",
                    "priority": 2
                }
            ],
            CommandType.X402_PRIVACY: [
                {
                    "pattern": re.compile(
                        r"(?:send|bridge|transfer)\s+.*(?:via\s+x402|using\s+x402|x402\s+privacy)",
                        re.IGNORECASE
                    ),
                    "description": "Explicit x402 privacy request",
                    "priority": 1
                }
            ],
            CommandType.BRIDGE_TO_PRIVACY: [
                {
                    "pattern": re.compile(
                        r"bridge\s+(?P<amount>[\d\.]+)\s+(?P<token>\w+)\s+to\s+(?P<dest_chain>zcash|privacy)",
                        re.IGNORECASE
                    ),
                    "description": "Bridge to Zcash/Privacy",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"make\s+(?:my\s+)?(?P<amount>[\d\.]+)\s+(?P<token>\w+)\s+private",
                        re.IGNORECASE
                    ),
                    "description": "Make funds private intent",
                    "priority": 2
                },
                {
                    "pattern": re.compile(
                        r"(?:send|transfer|move|bridge)\s+.*(?:private|privacy|zcash)",
                        re.IGNORECASE
                    ),
                    "description": "Transfer with privacy intent",
                    "priority": 3
                },
                {
                    "pattern": re.compile(
                        r"(?:want|need)\s+(?:to\s+)?(?:make|keep|send).*(?:private|privacy)",
                        re.IGNORECASE
                    ),
                    "description": "Privacy action intent",
                    "priority": 4
                }
            ],
            CommandType.SWAP: [
                {
                    "pattern": re.compile(
                        r"swap\s+\$(?P<amount>[\d\.]+)\s+worth\s+of\s+(?P<token_in>\w+)\s+(?:to|for)\s+(?P<token_out>\w+)",
                        re.IGNORECASE
                    ),
                    "amount_type": AmountType.USD_AMOUNT,
                    "description": "TRUE USD amount with 'worth of' phrasing",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"swap\s+(?P<amount>[\d\.]+)\s+dollars?\s+worth\s+of\s+(?P<token_in>\w+)\s+(?:to|for)\s+(?P<token_out>\w+)",
                        re.IGNORECASE
                    ),
                    "amount_type": AmountType.USD_AMOUNT,
                    "description": "TRUE USD amount with 'dollars worth of' phrasing",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"swap\s+\$(?P<amount>[\d\.]+)\s+of\s+(?P<token_in>\w+)\s+(?:to|for)\s+(?P<token_out>\w+)",
                        re.IGNORECASE
                    ),
                    "amount_type": AmountType.USD_AMOUNT,  # FIXED: This should be USD_AMOUNT
                    "description": "TRUE USD amount with $ symbol and 'of' phrasing",
                    "priority": 1  # Increased priority to match other USD patterns
                },
                {
                    "pattern": re.compile(
                        r"swap\s+(?P<amount>[\d\.]+)\s+(?P<token_in>\w+)\s+(?:to|for)\s+(?P<token_out>\w+)",
                        re.IGNORECASE
                    ),
                    "amount_type": AmountType.TOKEN_AMOUNT,
                    "description": "Standard token amount swap",
                    "priority": 3
                }
            ],
            CommandType.BRIDGE: [
                {
                    "pattern": re.compile(
                        r"bridge\s+(?P<amount>[\d\.]+)\s+(?P<token>\w+)\s+from\s+(?P<source_chain>\w+)\s+to\s+(?P<dest_chain>\w+)",
                        re.IGNORECASE
                    ),
                    "description": "Bridge with explicit source and destination chains",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"bridge\s+(?P<amount>[\d\.]+)\s+(?P<token>\w+)\s+to\s+(?P<dest_chain>\w+)",
                        re.IGNORECASE
                    ),
                    "description": "Bridge to destination chain",
                    "priority": 2
                },
                {
                    "pattern": re.compile(
                        r"bridge\s+\$(?P<amount>[\d\.]+)\s+of\s+(?P<token>\w+)\s+to\s+(?P<dest_chain>\w+)",
                        re.IGNORECASE
                    ),
                    "description": "Bridge with $ symbol and 'of' (token amount)",
                    "priority": 3
                }
            ],
            CommandType.TRANSFER: [
                {
                    "pattern": re.compile(
                        r"(?:transfer|send)\s+(?P<amount>[\d\.]+)\s+(?P<token>\w+)\s+to\s+(?P<destination>\S+)",
                        re.IGNORECASE
                    ),
                    "description": "Token transfer to address",
                    "priority": 1
                }
            ],
            CommandType.PAYMENT_ACTION: [
                {
                    "pattern": re.compile(
                        r"(?:create|new|make)\s+(?:a\s+)?(?:payment\s+)?(?:action|template|shortcut)",
                        re.IGNORECASE
                    ),
                    "description": "Create a new payment action",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"(?:show|list|view)\s+(?:my\s+)?(?:payment\s+)?(?:actions|templates|shortcuts)",
                        re.IGNORECASE
                    ),
                    "description": "List user's payment actions",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"(?:update|edit|modify)\s+(?:payment\s+)?(?:action|template|shortcut)",
                        re.IGNORECASE
                    ),
                    "description": "Update a payment action",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"(?:delete|remove)\s+(?:payment\s+)?(?:action|template|shortcut)",
                        re.IGNORECASE
                    ),
                    "description": "Delete a payment action",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"quick\s+actions",
                        re.IGNORECASE
                    ),
                    "description": "Get quick actions",
                    "priority": 1
                }
            ],
            CommandType.BALANCE: [
                {
                    "pattern": re.compile(
                        r"(?:balance|check balance)(?:\s+(?P<token>\w+))?",
                        re.IGNORECASE
                    ),
                    "description": "Check token balance",
                    "priority": 1
                }
            ],
            CommandType.PROTOCOL_RESEARCH: [
                {
                    "pattern": re.compile(
                        r"(?:quick|quick research):\s*(?:research|tell me about|what is|about|info on|explain)\s+(?P<protocol>\w+)",
                        re.IGNORECASE
                    ),
                    "description": "Quick research DeFi protocol",
                    "research_mode": "quick",
                    "priority": 1
                },
                {
                    "pattern": re.compile(
                        r"(?:deep|deep research):\s*(?:research|tell me about|what is|about|info on|explain)\s+(?P<protocol>\w+)",
                        re.IGNORECASE
                    ),
                    "description": "Deep research DeFi protocol",
                    "research_mode": "deep",
                    "priority": 2
                },
                {
                    "pattern": re.compile(
                        r"(?:research|tell me about|what is|about|info on|explain)\s+(?P<protocol>\w+)\s+(?:quick|quick research)",
                        re.IGNORECASE
                    ),
                    "description": "Research DeFi protocol (quick mode suffix)",
                    "research_mode": "quick",
                    "priority": 3
                },
                {
                    "pattern": re.compile(
                        r"(?:research|tell me about|what is|about|info on|explain)\s+(?P<protocol>\w+)\s+(?:deep|deep research)",
                        re.IGNORECASE
                    ),
                    "description": "Research DeFi protocol (deep mode suffix)",
                    "research_mode": "deep",
                    "priority": 4
                },
                {
                    "pattern": re.compile(
                        r"(?:research|tell me about|what is|about|info on|explain)\s+(?P<protocol>\w+)",
                        re.IGNORECASE
                    ),
                    "description": "Research DeFi protocol (default quick)",
                    "research_mode": "quick",
                    "priority": 5
                }
            ]
        }

    def parse_command(self, command: str) -> Tuple[CommandType, Optional[CommandDetails]]:
        """
        Parse command with intelligent amount detection and validation.
        Returns command type and parsed details.
        """
        command_clean = command.lower().strip()

        # Check cache first
        if command_clean in self._pattern_cache:
            return self._pattern_cache[command_clean]

        # Try each command type in priority order
        for command_type, patterns in self._patterns.items():
            for pattern_info in sorted(patterns, key=lambda x: x["priority"]):
                match = pattern_info["pattern"].search(command_clean)
                if match:
                    try:
                        details = self._extract_details(command_type, match, pattern_info)
                        result = (command_type, details)

                        # Cache successful parse
                        self._pattern_cache[command_clean] = result
                        return result

                    except Exception as e:
                        logger.warning(f"Failed to extract details for {command_type}: {e}")
                        continue

        # No match found
        result = (CommandType.UNKNOWN, None)
        self._pattern_cache[command_clean] = result
        return result

    def _extract_details(self, command_type: CommandType, match: re.Match,
                         pattern_info: Dict[str, Any]) -> CommandDetails:
         """Extract command details based on command type."""

         if command_type == CommandType.SWAP:
             return self._extract_swap_details(match, pattern_info)
         elif command_type == CommandType.BRIDGE:
             return self._extract_bridge_details(match)
         elif command_type == CommandType.TRANSFER:
             return self._extract_transfer_details(match)
         elif command_type == CommandType.BALANCE:
             return self._extract_balance_details(match)
         elif command_type == CommandType.PROTOCOL_RESEARCH:
             return self._extract_research_details(match, pattern_info)
         elif command_type == CommandType.BRIDGE_TO_PRIVACY:
             return self._extract_bridge_to_privacy_details(match)
         elif command_type == CommandType.CONTEXTUAL_QUESTION:
             # For contextual questions, no structured details needed
             return CommandDetails()

         return CommandDetails()

    def _extract_swap_details(self, match: re.Match, pattern_info: Dict[str, Any]) -> CommandDetails:
        """Extract swap details with intelligent amount parsing."""

        groups = match.groupdict()
        amount_type = pattern_info.get("amount_type", AmountType.TOKEN_AMOUNT)

        # Parse amount intelligently
        if amount_type == AmountType.USD_AMOUNT:
            # TRUE USD amount - need to convert to token amount later
            usd_value = self._parse_decimal(groups["amount"])
            parsed_amount = ParsedAmount(
                value=usd_value,
                amount_type=AmountType.USD_AMOUNT,
                token_symbol=groups["token_in"].upper(),
                original_text=f"${usd_value} worth of {groups['token_in']}"
            )
        else:
            # Token amount - direct parsing
            token_amount = self._parse_decimal(groups["amount"])
            parsed_amount = ParsedAmount(
                value=token_amount,
                amount_type=AmountType.TOKEN_AMOUNT,
                token_symbol=groups["token_in"].upper(),
                original_text=f"{token_amount} {groups['token_in']}"
            )

        return CommandDetails(
            amount=float(parsed_amount.value),
            token_in=TokenInfo(symbol=parsed_amount.token_symbol),
            token_out=TokenInfo(symbol=groups["token_out"].upper()),
            is_usd_amount=(amount_type == AmountType.USD_AMOUNT),
            additional_params={
                "parsed_amount": parsed_amount.to_dict(),
                "amount_type": parsed_amount.amount_type.value,
                "original_command": match.string
            }
        )

    def _extract_bridge_details(self, match: re.Match) -> CommandDetails:
        """Extract bridge details."""
        groups = match.groupdict()
        amount = self._parse_decimal(groups["amount"])
        
        # Check if it's a USD amount (bridge $1 of eth to ...)
        is_usd = "$" in match.string or "usd" in match.string.lower() or "dollar" in match.string.lower()

        return CommandDetails(
            amount=float(amount),
            token_in=TokenInfo(symbol=groups["token"].upper()),
            source_chain=groups.get("source_chain"),
            destination_chain=groups["dest_chain"],
            is_usd_amount=is_usd
        )

    def _extract_bridge_to_privacy_details(self, match: re.Match) -> CommandDetails:
        """Extract bridge to privacy details."""
        groups = match.groupdict()
        
        # Handle case where amount/token are not present (general privacy inquiry)
        amount = None
        token = None
        
        if "amount" in groups and groups["amount"]:
            try:
                amount = self._parse_decimal(groups["amount"])
            except (ValueError, KeyError):
                pass
        
        if "token" in groups and groups["token"]:
            token = groups["token"].upper()
        
        return CommandDetails(
            amount=float(amount) if amount else None,
            token_in=TokenInfo(symbol=token) if token else None,
            destination_chain="Zcash",
            additional_params={"is_privacy": True}
        )

    def _extract_transfer_details(self, match: re.Match) -> CommandDetails:
        """Extract transfer details."""
        groups = match.groupdict()
        amount = self._parse_decimal(groups["amount"])

        return CommandDetails(
            amount=float(amount),
            token_in=TokenInfo(symbol=groups["token"].upper()),
            destination=groups["destination"]
        )

    def _extract_balance_details(self, match: re.Match) -> CommandDetails:
        """Extract balance details."""
        groups = match.groupdict()
        token = groups.get("token")

        if token:
            return CommandDetails(token_in=TokenInfo(symbol=token.upper()))
        return CommandDetails()

    def _extract_research_details(self, match: re.Match, pattern_info: Dict[str, Any]) -> CommandDetails:
         """Extract protocol research details including research mode."""
         groups = match.groupdict()
         research_mode = pattern_info.get("research_mode", "quick")  # Default to quick
         
         return CommandDetails(
             protocol=groups["protocol"],
             additional_params={
                 "research_type": "protocol",
                 "research_mode": research_mode
             }
         )

    def _parse_decimal(self, amount_str: str) -> Decimal:
        """Parse amount string to Decimal with validation."""
        try:
            # Remove any non-numeric characters except decimal point
            clean_amount = re.sub(r'[^\d.]', '', amount_str)
            return Decimal(clean_amount)
        except (InvalidOperation, ValueError) as e:
            raise ValueError(f"Invalid amount format: {amount_str}") from e

    def validate_command(self, unified_command: UnifiedCommand) -> ValidationResult:
        """Validate unified command with comprehensive checks."""
        missing_requirements = []

        # Wallet and chain requirements for transactions
        transaction_commands = [CommandType.TRANSFER, CommandType.BRIDGE, CommandType.SWAP]
        if unified_command.command_type in transaction_commands:
            if not unified_command.wallet_address:
                missing_requirements.append("wallet_address")
            if not unified_command.chain_id:
                missing_requirements.append("chain_id")

        # Command-specific validation
        if unified_command.command_type == CommandType.SWAP:
            if not unified_command.details:
                missing_requirements.append("swap_details")
            elif not unified_command.details.amount or unified_command.details.amount <= 0:
                missing_requirements.append("valid_swap_amount")
            elif not unified_command.details.token_in or not unified_command.details.token_out:
                missing_requirements.append("swap_tokens")

        elif unified_command.command_type == CommandType.BRIDGE:
            if not unified_command.details:
                missing_requirements.append("bridge_details")
            elif not unified_command.details.amount or unified_command.details.amount <= 0:
                missing_requirements.append("valid_bridge_amount")
            elif not unified_command.details.destination_chain:
                missing_requirements.append("destination_chain")

        elif unified_command.command_type == CommandType.TRANSFER:
            if not unified_command.details:
                missing_requirements.append("transfer_details")
            elif not unified_command.details.amount or unified_command.details.amount <= 0:
                missing_requirements.append("valid_transfer_amount")
            elif not unified_command.details.destination:
                missing_requirements.append("destination_address")

        # Generate appropriate error messages
        is_valid = len(missing_requirements) == 0
        error_message = None

        if not is_valid:
            if "wallet_address" in missing_requirements:
                error_message = "Please connect your wallet to perform this operation."
            elif "chain_id" in missing_requirements:
                error_message = "Please connect to a supported network."
            elif "valid_swap_amount" in missing_requirements:
                error_message = "Please specify a valid amount to swap (greater than 0)."
            elif "valid_bridge_amount" in missing_requirements:
                error_message = "Please specify a valid amount to bridge (greater than 0)."
            elif "valid_transfer_amount" in missing_requirements:
                error_message = "Please specify a valid amount to transfer (greater than 0)."
            else:
                error_message = f"Missing required information: {', '.join(missing_requirements)}"

        return ValidationResult(
            is_valid=is_valid,
            error_message=error_message,
            missing_requirements=missing_requirements
        )

    def create_unified_command(
        self,
        command: str,
        wallet_address: Optional[str] = None,
        chain_id: Optional[int] = None,
        user_name: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ) -> UnifiedCommand:
        """Create unified command with consolidated parsing."""
        command_type, details = self.parse_command(command)
        
        # Extract research_mode if present in details
        research_mode = "quick"  # Default
        if details and details.additional_params:
            research_mode = details.additional_params.get("research_mode", "quick")

        return UnifiedCommand(
            command=command,
            command_type=command_type,
            wallet_address=wallet_address,
            chain_id=chain_id,
            user_name=user_name,
            openai_api_key=openai_api_key,
            details=details,
            research_mode=research_mode
        )

    def clear_cache(self):
        """Clear pattern cache for testing."""
        self._pattern_cache.clear()

    def get_supported_patterns(self, command_type: CommandType) -> List[str]:
        """Get supported pattern descriptions for a command type."""
        if command_type not in self._patterns:
            return []

        return [pattern["description"] for pattern in self._patterns[command_type]]


# Global instance following singleton pattern for performance
unified_parser = UnifiedParser()