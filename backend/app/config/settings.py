"""
Centralized configuration management for SNEL backend.
Single source of truth for all application settings.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from functools import lru_cache


@dataclass(frozen=True)
class APISettings:
    """API-related configuration."""
    timeout: int = field(default_factory=lambda: int(os.getenv("API_TIMEOUT", "30")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("API_MAX_RETRIES", "3")))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("API_RATE_LIMIT", "60")))
    max_request_size: int = field(default_factory=lambda: int(os.getenv("API_MAX_REQUEST_SIZE", "10485760")))  # 10MB


@dataclass
class ExternalServiceSettings:
    """External service configuration."""
    # Brian API
    brian_api_url: str = field(default_factory=lambda: os.getenv("BRIAN_API_URL", "https://api.brian.ai"))
    brian_api_key: str = field(default_factory=lambda: os.getenv("BRIAN_API_KEY", ""))
    
    # Exa API
    exa_api_url: str = field(default_factory=lambda: os.getenv("EXA_API_URL", "https://api.exa.ai"))
    exa_api_key: str = field(default_factory=lambda: os.getenv("EXA_API_KEY", ""))
    
    # Firecrawl API
    firecrawl_api_url: str = field(default_factory=lambda: os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev"))
    firecrawl_api_key: str = field(default_factory=lambda: os.getenv("FIRECRAWL_API_KEY", ""))
    
    # OpenAI API
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))


@dataclass(frozen=True)
class DatabaseSettings:
    """Database and caching configuration."""
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
    redis_db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    redis_max_connections: int = field(default_factory=lambda: int(os.getenv("REDIS_MAX_CONNECTIONS", "10")))
    
    # Payment actions storage backend
    payment_actions_backend: str = field(default_factory=lambda: os.getenv("PAYMENT_ACTIONS_BACKEND", "redis"))
    # Options: "memory" (dev), "redis" (default), "postgresql" (production)
    
    # Cache TTL settings (in seconds)
    cache_ttl_short: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_SHORT", "60")))      # 1 minute
    cache_ttl_medium: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_MEDIUM", "300")))   # 5 minutes
    cache_ttl_long: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_LONG", "3600")))     # 1 hour


@dataclass(frozen=True)
class ChainSettings:
    """Blockchain configuration."""
    supported_chains: Dict[int, str] = field(default_factory=lambda: {
        1: "ethereum",
        8453: "base", 
        42161: "arbitrum",
        10: "optimism",
        137: "polygon",
        43114: "avalanche",
        56: "bsc",
        534352: "scroll",
        59144: "linea",
        5000: "mantle",
        81457: "blast",
        324: "zksync",
        34443: "mode",
        100: "gnosis",
        167000: "taiko",
        25: "cronos",          # Cronos Mainnet
        338: "cronos-testnet"  # Cronos Testnet
    })
    
    default_chain_id: int = field(default_factory=lambda: int(os.getenv("DEFAULT_CHAIN_ID", "1")))
    
    # RPC URLs
    rpc_urls: Dict[int, str] = field(default_factory=lambda: {
        1: os.getenv("ETHEREUM_RPC_URL", ""),
        8453: os.getenv("BASE_RPC_URL", ""),
        42161: os.getenv("ARBITRUM_RPC_URL", ""),
        10: os.getenv("OPTIMISM_RPC_URL", ""),
        137: os.getenv("POLYGON_RPC_URL", ""),
    })


@dataclass(frozen=True)
class SecuritySettings:
    """Security-related configuration."""
    allowed_origins: List[str] = field(default_factory=lambda: 
        os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]
    )
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    jwt_expiration_hours: int = field(default_factory=lambda: int(os.getenv("JWT_EXPIRATION_HOURS", "24")))


@dataclass(frozen=True)
class LoggingSettings:
    """Logging configuration."""
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = field(default_factory=lambda: os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    file_path: Optional[str] = field(default_factory=lambda: os.getenv("LOG_FILE_PATH"))
    max_file_size: int = field(default_factory=lambda: int(os.getenv("LOG_MAX_FILE_SIZE", "10485760")))  # 10MB
    backup_count: int = field(default_factory=lambda: int(os.getenv("LOG_BACKUP_COUNT", "5")))


@dataclass(frozen=True)
class Settings:
    """Main application settings container."""
    # Environment
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    
    # Sub-configurations
    api: APISettings = field(default_factory=APISettings)
    external_services: ExternalServiceSettings = field(default_factory=ExternalServiceSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    chains: ChainSettings = field(default_factory=ChainSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_required_settings()
        self._validate_environment_specific_settings()
    
    def _validate_required_settings(self):
        """Validate that required settings are present."""
        required_for_production = [
            (self.external_services.brian_api_key, "BRIAN_API_KEY"),
            (self.security.secret_key != "dev-secret-key-change-in-production", "SECRET_KEY"),
        ]
        
        if self.environment == "production":
            for value, setting_name in required_for_production:
                if not value:
                    raise ValueError(f"{setting_name} is required in production environment")
    
    def _validate_environment_specific_settings(self):
        """Validate environment-specific settings."""
        if self.environment == "production":
            if self.debug:
                raise ValueError("DEBUG should be False in production")
            if "*" in self.security.allowed_origins:
                raise ValueError("ALLOWED_ORIGINS should not include '*' in production")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == "testing"


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (cached).
    This ensures we only create the settings object once.
    """
    return Settings()


# Convenience function for accessing settings
def get_config() -> Settings:
    """Get the current application configuration."""
    return get_settings()
