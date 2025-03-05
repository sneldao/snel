from pydantic import BaseModel, Field
from typing import Optional

class Token(BaseModel):
    """
    Model representing a token.
    """
    address: str = Field(..., description="The token's contract address")
    symbol: str = Field(..., description="The token's symbol (e.g., 'ETH', 'USDC')")
    name: str = Field(..., description="The token's full name")
    decimals: int = Field(default=18, description="Number of decimal places")
    chain_id: int = Field(..., description="The chain ID where this token exists")
    verified: bool = Field(default=True, description="Whether the token is verified")
    source: str = Field(default="openocean", description="Source of the token information")
    logo_uri: Optional[str] = Field(None, description="URI of the token's logo")
    price_usd: Optional[float] = Field(None, description="Current price in USD")
    
    class Config:
        json_schema_extra = {
            "example": {
                "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "symbol": "WETH",
                "name": "Wrapped Ether",
                "decimals": 18,
                "chain_id": 1,
                "verified": True,
                "source": "openocean",
                "logo_uri": "https://example.com/weth.png",
                "price_usd": 2000.00
            }
        } 