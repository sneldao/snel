import os
from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field

class KyberSettings(BaseSettings):
    """Kyber Swap API configuration."""
    api_url: str = "https://aggregator-api.kyberswap.com"
    slippage_tolerance: int = 300  # 3.0% in basis points
    gas_limit: str = "500000"  # Default gas limit for swaps
    deadline_seconds: int = 3600  # 1 hour
    retry_count: int = 3
    retry_delay: float = 1.0  # seconds
    disable_ssl_verify: bool = Field(
        default=False, 
        description="Disable SSL verification (development only)"
    )
    
    model_config = {
        "env_prefix": "KYBER_",
        "extra": "allow"
    }

class TokenSettings(BaseSettings):
    """Token-related configuration."""
    default_decimals: int = 18
    usdc_decimals: int = 6
    usdt_decimals: int = 6
    dai_decimals: int = 18
    
    model_config = {
        "env_prefix": "TOKEN_",
        "extra": "allow"
    }

class APISettings(BaseSettings):
    """API-related configuration."""
    default_gas_limit: str = "0x186a0"  # 100,000 gas
    default_timeout: float = 30.0  # seconds
    
    model_config = {
        "env_prefix": "API_",
        "extra": "allow"
    }

class Settings(BaseSettings):
    """Main application settings."""
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Nested settings
    kyber: KyberSettings = Field(default_factory=KyberSettings)
    token: TokenSettings = Field(default_factory=TokenSettings)
    api: APISettings = Field(default_factory=APISettings)
    
    # Router addresses by chain
    router_addresses: Dict[int, str] = {
        1: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",      # Ethereum
        137: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",    # Polygon
        42161: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Arbitrum
        10: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",     # Optimism
        8453: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",   # Base
        534352: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5", # Scroll
    }
    
    # Token decimals mapping
    token_decimals: Dict[str, int] = {
        "ETH": 18,
        "WETH": 18,
        "USDC": 6,
        "USDT": 6,
        "DAI": 18,
        "NURI": 18,
    }
    
    # API keys and other settings that might be in environment variables
    alchemy_key: str = Field(default="", env="ALCHEMY_KEY")
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    quicknode_endpoint: str = Field(default="", env="QUICKNODE_ENDPOINT")
    coingecko_api_key: str = Field(default="", env="COINGECKO_API_KEY")
    moralis_api_key: str = Field(default="", env="MORALIS_API_KEY")
    redis_url: str = Field(default="", env="REDIS_URL")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    quicknode_api_key: str = Field(default="", env="QUICKNODE_API_KEY")
    disable_ssl_verify: bool = Field(default=False, env="DISABLE_SSL_VERIFY")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow"  # Allow extra fields from environment variables
    }

# Create a global settings instance
settings = Settings() 