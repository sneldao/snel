"""
Privacy Service - Chain-aware privacy routing and management
"""
from typing import Dict, Optional, List
from decimal import Decimal
from app.config.chains import (
    get_privacy_capabilities,
    is_x402_privacy_supported,
    is_gmp_privacy_supported,
    is_compliance_supported
)
from app.models.unified_models import PrivacyLevel, ChainPrivacyRoute
from app.core.config_manager import ConfigurationManager
import logging

logger = logging.getLogger(__name__)

class PrivacyService:
    """Chain-aware privacy service for routing transactions through optimal privacy paths."""
    
    def __init__(self, config):
        self.config = config
        
    async def get_optimal_privacy_route(
        self,
        source_chain_id: int,
        destination: str,
        privacy_level: PrivacyLevel
    ) -> ChainPrivacyRoute:
        """
        Get the optimal privacy route based on chain capabilities.
        
        Args:
            source_chain_id: Source chain ID
            destination: Destination (address or chain name)
            privacy_level: Desired privacy level
            
        Returns:
            ChainPrivacyRoute with optimal path and capabilities
        """
        # Determine if destination is Zcash (direct privacy)
        is_zcash_destination = destination.startswith(('zcash:', 'zcash:', 'u1', 't1', 't3'))
        
        # Check chain capabilities
        capabilities = get_privacy_capabilities(source_chain_id)
        
        # Route selection logic
        if is_zcash_destination:
            # Direct Zcash route
            if capabilities.direct_zcash:
                return ChainPrivacyRoute(
                    method="direct_zcash",
                    privacy_level=privacy_level,
                    estimated_latency="5-10min",
                    capabilities={
                        "compliance": capabilities.compliance_support,
                        "fallback": False
                    }
                )
            elif capabilities.gmp_privacy:
                return ChainPrivacyRoute(
                    method="gmp_privacy",
                    privacy_level=privacy_level,
                    estimated_latency="2-5min",
                    capabilities={
                        "compliance": capabilities.compliance_support,
                        "fallback": True
                    }
                )
        else:
            # Cross-chain privacy route
            if capabilities.x402_support and privacy_level != PrivacyLevel.COMPLIANCE:
                return ChainPrivacyRoute(
                    method="x402_privacy",
                    privacy_level=privacy_level,
                    estimated_latency="1-2min",
                    capabilities={
                        "compliance": False,
                        "fallback": False
                    }
                )
            elif capabilities.gmp_privacy:
                return ChainPrivacyRoute(
                    method="gmp_privacy",
                    privacy_level=privacy_level,
                    estimated_latency="2-5min",
                    capabilities={
                        "compliance": capabilities.compliance_support,
                        "fallback": True
                    }
                )
        
        # No privacy available
        raise PrivacyRoutingError(
            f"No privacy route available from chain {source_chain_id} "
            f"for privacy level {privacy_level}"
        )
    
    async def get_chain_privacy_options(self, chain_id: int) -> List[Dict[str, str]]:
        """Get available privacy options for a specific chain."""
        capabilities = get_privacy_capabilities(chain_id)
        
        options = [
            {
                "value": "public",
                "label": "Public Transaction",
                "description": "Standard transaction on public blockchain"
            }
        ]
        
        if capabilities.x402_support:
            options.append({
                "value": "private",
                "label": "Private via x402",
                "description": "Fast privacy using x402 programmatic payments"
            })
            if capabilities.compliance_support:
                options.append({
                    "value": "compliance",
                    "label": "Private with Compliance",
                    "description": "Private transaction with regulatory records"
                })
        elif capabilities.gmp_privacy:
            options.append({
                "value": "private",
                "label": "Private via GMP",
                "description": "Privacy using GMP bridge (slower)"
            })
        
        return options
    
    async def validate_privacy_request(
        self,
        chain_id: int,
        privacy_level: PrivacyLevel
    ) -> bool:
        """Validate if a privacy request is possible on a specific chain."""
        capabilities = get_privacy_capabilities(chain_id)
        
        if privacy_level == PrivacyLevel.PUBLIC:
            return True
        elif privacy_level == PrivacyLevel.PRIVATE:
            return capabilities.x402_support or capabilities.gmp_privacy
        elif privacy_level == PrivacyLevel.COMPLIANCE:
            return capabilities.compliance_support and (capabilities.x402_support or capabilities.gmp_privacy)
        
        return False

class PrivacyRoutingError(Exception):
    """Error raised when privacy routing fails."""
    pass

# Add PrivacyLevel enum if not already defined
try:
    from app.models.unified_models import PrivacyLevel
except ImportError:
    from enum import Enum
    
    class PrivacyLevel(Enum):
        PUBLIC = "public"
        PRIVATE = "private" 
        COMPLIANCE = "compliance"

# Add ChainPrivacyRoute model if not already defined
try:
    from app.models.unified_models import ChainPrivacyRoute
except ImportError:
    from typing import TypedDict
    
    class ChainPrivacyRoute(TypedDict):
        method: str
        privacy_level: PrivacyLevel
        estimated_latency: str
        capabilities: Dict[str, bool]