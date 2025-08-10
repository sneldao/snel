"""
Enhanced command patterns with intelligent detection and maintainable structure.
Optimized for performance, clarity, and extensibility.
"""
import re
from typing import Dict, List, Tuple, Optional, NamedTuple
from enum import Enum
from dataclasses import dataclass

from app.models.unified_models import CommandType


class PatternPriority(Enum):
    """Pattern matching priority levels."""
    HIGH = 1      # Exact, specific patterns
    MEDIUM = 2    # Common patterns
    LOW = 3       # Flexible, catch-all patterns


@dataclass
class CommandPattern:
    """Structured command pattern with metadata."""
    pattern: str
    command_type: CommandType
    priority: PatternPriority
    description: str
    examples: List[str]
    
    def __post_init__(self):
        """Compile regex pattern for performance."""
        self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE)


class EnhancedCommandPatterns:
    """
    Enhanced command pattern system with intelligent detection.
    Designed for maintainability, performance, and user delight.
    """
    
    def __init__(self):
        """Initialize with optimized pattern hierarchy."""
        self.patterns = self._build_pattern_hierarchy()
        self._pattern_cache = {}  # Performance optimization
    
    def _build_pattern_hierarchy(self) -> Dict[PatternPriority, List[CommandPattern]]:
        """Build hierarchical pattern system for optimal matching."""
        
        patterns = {
            PatternPriority.HIGH: [
                # Exact cross-chain swap patterns (highest priority)
                CommandPattern(
                    pattern=r"swap\s+(?P<amount>[\d\.]+)\s+(?P<token_in>\w+)\s+from\s+(?P<source_chain>\w+)\s+(?:to|for)\s+(?P<token_out>\w+)\s+on\s+(?P<dest_chain>\w+)",
                    command_type=CommandType.CROSS_CHAIN_SWAP,
                    priority=PatternPriority.HIGH,
                    description="Explicit cross-chain swap with source and destination chains",
                    examples=[
                        "swap 100 USDC from Ethereum to MATIC on Polygon",
                        "swap 50 ETH from Ethereum for USDC on Arbitrum"
                    ]
                ),
                CommandPattern(
                    pattern=r"swap\s+(?P<amount>[\d\.]+)\s+(?P<token_in>\w+)\s+on\s+(?P<source_chain>\w+)\s+(?:to|for)\s+(?P<token_out>\w+)\s+on\s+(?P<dest_chain>\w+)",
                    command_type=CommandType.CROSS_CHAIN_SWAP,
                    priority=PatternPriority.HIGH,
                    description="Cross-chain swap with explicit chain specification",
                    examples=[
                        "swap 100 USDC on Ethereum to MATIC on Polygon",
                        "swap 50 DAI on Ethereum for USDC on Base"
                    ]
                ),
                
                # Exact GMP operation patterns
                CommandPattern(
                    pattern=r"(?:call|execute|trigger)\s+(?P<function>\w+)\s*(?:\(\s*\))?\s+(?:function\s+)?on\s+(?P<dest_chain>\w+)(?:\s+(?:contract|address)\s+(?P<contract>\S+))?",
                    command_type=CommandType.GMP_OPERATION,
                    priority=PatternPriority.HIGH,
                    description="Direct contract function calls on destination chains",
                    examples=[
                        "call mint function on Polygon",
                        "execute stake() on Arbitrum contract 0x123...",
                        "trigger claim on Base"
                    ]
                ),
            ],
            
            PatternPriority.MEDIUM: [
                # Cross-chain keywords with flexible matching
                CommandPattern(
                    pattern=r"cross[\s\-]?chain\s+swap\s+(?P<amount>[\d\.]+)\s+(?P<token_in>\w+)\s+(?:to|for)\s+(?P<token_out>\w+)",
                    command_type=CommandType.CROSS_CHAIN_SWAP,
                    priority=PatternPriority.MEDIUM,
                    description="Cross-chain swap with explicit cross-chain keyword",
                    examples=[
                        "cross-chain swap 100 USDC to MATIC",
                        "cross chain swap 50 ETH for DAI"
                    ]
                ),
                CommandPattern(
                    pattern=r"bridge\s+and\s+swap\s+(?P<amount>[\d\.]+)\s+(?P<token_in>\w+)\s+(?:to|for)\s+(?P<token_out>\w+)",
                    command_type=CommandType.CROSS_CHAIN_SWAP,
                    priority=PatternPriority.MEDIUM,
                    description="Bridge and swap operation",
                    examples=[
                        "bridge and swap 100 USDC to MATIC",
                        "bridge and swap 50 DAI for USDC"
                    ]
                ),
                
                # Complex DeFi operations across chains
                CommandPattern(
                    pattern=r"(?P<action>add\s+liquidity|provide\s+liquidity|stake|farm|lend|borrow)\s+.*(?:to|in)\s+(?P<protocol>\w+)\s+on\s+(?P<dest_chain>\w+)\s+using\s+.*from\s+(?P<source_chain>\w+)",
                    command_type=CommandType.GMP_OPERATION,
                    priority=PatternPriority.MEDIUM,
                    description="Complex DeFi operations across chains",
                    examples=[
                        "add liquidity to Uniswap on Arbitrum using ETH from Ethereum",
                        "stake tokens in Aave on Polygon using funds from Ethereum"
                    ]
                ),
                
                # Regular operations (maintain existing functionality)
                CommandPattern(
                    pattern=r"swap\s+(?P<amount>[\d\.]+)\s+(?P<token_in>\w+)\s+(?:to|for)\s+(?P<token_out>\w+)(?!\s+(?:from|on))",
                    command_type=CommandType.SWAP,
                    priority=PatternPriority.MEDIUM,
                    description="Same-chain token swap",
                    examples=[
                        "swap 1 ETH for USDC",
                        "swap 100 USDC to DAI"
                    ]
                ),
                CommandPattern(
                    pattern=r"bridge\s+(?P<amount>[\d\.]+)\s+(?P<token>\w+)\s+(?:from\s+(?P<source_chain>\w+)\s+)?to\s+(?P<dest_chain>\w+)",
                    command_type=CommandType.BRIDGE,
                    priority=PatternPriority.MEDIUM,
                    description="Cross-chain token bridge",
                    examples=[
                        "bridge 100 USDC to Arbitrum",
                        "bridge 0.1 ETH from Ethereum to Polygon"
                    ]
                ),
                
                # Balance check patterns
                CommandPattern(
                    pattern=r"(?:balance|check balance)(?:\s+(?P<token>\w+))?",
                    command_type=CommandType.BALANCE,
                    priority=PatternPriority.MEDIUM,
                    description="Check token balance",
                    examples=[
                        "balance",
                        "check balance ETH",
                        "balance USDC"
                    ]
                ),
                
                # Protocol research patterns
                CommandPattern(
                    pattern=r"(?:research|tell me about|what is|about|info on|explain)\s+(?P<protocol>\w+)",
                    command_type=CommandType.PROTOCOL_RESEARCH,
                    priority=PatternPriority.MEDIUM,
                    description="Research DeFi protocol",
                    examples=[
                        "research Uniswap",
                        "tell me about Aave",
                        "what is Compound"
                    ]
                ),
            ],
            
            PatternPriority.LOW: [
                # Flexible patterns for edge cases
                CommandPattern(
                    pattern=r"swap.*(?P<token_in>\w+).*(?:from|on).*(?P<source_chain>\w+).*(?:to|for).*(?P<token_out>\w+).*(?:on|to).*(?P<dest_chain>\w+)",
                    command_type=CommandType.CROSS_CHAIN_SWAP,
                    priority=PatternPriority.LOW,
                    description="Flexible cross-chain swap detection",
                    examples=[
                        "I want to swap some USDC from Ethereum for MATIC on Polygon",
                        "Can you swap my ETH on Ethereum to USDC on Base?"
                    ]
                ),
                CommandPattern(
                    pattern=r"(?:transfer|send)\s+(?P<amount>[\d\.]+)\s+(?P<token>\w+)\s+to\s+(?P<destination>\S+)",
                    command_type=CommandType.TRANSFER,
                    priority=PatternPriority.LOW,
                    description="Token transfer to address",
                    examples=[
                        "transfer 0.1 ETH to 0x123...",
                        "send 100 USDC to vitalik.eth"
                    ]
                ),
            ]
        }
        
        return patterns
    
    def detect_command_type(self, command: str) -> Tuple[CommandType, Optional[Dict]]:
        """
        Detect command type with intelligent priority-based matching.
        Returns command type and extracted parameters.
        """
        command_clean = command.lower().strip()
        
        # Check cache for performance
        if command_clean in self._pattern_cache:
            return self._pattern_cache[command_clean]
        
        # Match patterns by priority (HIGH -> MEDIUM -> LOW)
        for priority in [PatternPriority.HIGH, PatternPriority.MEDIUM, PatternPriority.LOW]:
            for pattern in self.patterns[priority]:
                match = pattern.compiled_pattern.search(command_clean)
                if match:
                    result = (pattern.command_type, match.groupdict())
                    self._pattern_cache[command_clean] = result
                    return result
        
        # No match found
        result = (CommandType.UNKNOWN, None)
        self._pattern_cache[command_clean] = result
        return result
    
    def get_pattern_examples(self, command_type: CommandType) -> List[str]:
        """Get example commands for a specific command type."""
        examples = []
        for priority_patterns in self.patterns.values():
            for pattern in priority_patterns:
                if pattern.command_type == command_type:
                    examples.extend(pattern.examples)
        return examples
    
    def get_supported_operations(self) -> Dict[CommandType, List[str]]:
        """Get all supported operations with examples."""
        operations = {}
        for priority_patterns in self.patterns.values():
            for pattern in priority_patterns:
                if pattern.command_type not in operations:
                    operations[pattern.command_type] = []
                operations[pattern.command_type].extend(pattern.examples)
        return operations
    
    def clear_cache(self):
        """Clear pattern cache (useful for testing)."""
        self._pattern_cache.clear()


# Global instance for performance
enhanced_patterns = EnhancedCommandPatterns()
