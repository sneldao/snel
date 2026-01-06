"""Structured models for protocol knowledge base entries."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ProtocolMetrics(BaseModel):
    """Dynamic metrics that change frequently (refreshed hourly/daily)."""
    tvl: Optional[str] = None  # Total Value Locked
    volume_24h: Optional[str] = None
    market_cap: Optional[str] = None
    apy_yield: Optional[str] = None
    fees: Optional[Dict[str, str]] = None  # e.g., {"swap": "0.05%", "LP": "0.3%"}
    last_updated: Optional[datetime] = None
    source: Optional[str] = None  # "firecrawl", "coingecko", etc.


class ProtocolEntry(BaseModel):
    """Complete protocol knowledge base entry with structured schema."""
    
    # Identity
    official_name: str
    type: str  # e.g., "DEX", "Lending", "Stablecoin", "Privacy Protocol"
    aliases: List[str] = Field(default_factory=list)
    
    # Core information
    summary: str
    key_features: List[str] = Field(default_factory=list)
    how_it_works: Optional[str] = None
    use_cases: List[str] = Field(default_factory=list)
    
    # Privacy/security specifics
    privacy_explanation: Optional[str] = None
    technical_explanation: Optional[str] = None
    
    # Financial/governance
    governance_token: Optional[str] = None
    launch_date: Optional[str] = None
    
    # Security & audits
    security_info: Optional[str] = None
    audits: List[Dict[str, str]] = Field(
        default_factory=list,  # [{"firm": "Trail of Bits", "date": "2023-06", "status": "passed"}]
    )
    
    # Infrastructure
    contracts: Dict[str, str] = Field(
        default_factory=dict,  # {"ethereum": "0x...", "polygon": "0x..."}
    )
    recommended_wallets: List[Dict[str, str]] = Field(default_factory=list)
    
    # Relationships
    integrations_with: List[str] = Field(
        default_factory=list,  # ["uniswap", "aave", "curve"]
    )
    bridges_to: List[str] = Field(
        default_factory=list,  # ["ethereum", "polygon", "base"]
    )
    competes_with: List[str] = Field(
        default_factory=list,  # For stablecoins: ["usdc", "usdt", "dai"]
    )
    
    # Multi-language support
    names: Dict[str, str] = Field(
        default_factory=dict,  # {"en": "...", "es": "...", "zh": "..."}
    )
    
    # Metadata
    from_knowledge_base: bool = True
    last_verified: Optional[datetime] = None
    source_url: Optional[str] = None
    
    # Domain-specific fields (extensible)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "official_name": "MNEE Stablecoin",
                "type": "Stablecoin for Commerce & Payments",
                "aliases": ["mnee token", "mnee stablecoin"],
                "summary": "MNEE is a programmable stablecoin...",
                "key_features": ["Stable value pegged to USD", "..."],
                "governance_token": None,
                "audits": [{"firm": "Firm Name", "date": "2024-01", "status": "passed"}],
                "integrations_with": ["uniswap", "aave"],
                "names": {"en": "MNEE Stablecoin", "es": "Moneda MNEE"},
            }
        }
