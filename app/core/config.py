"""
Configuration module for the application.
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings class.
    
    This class loads settings from environment variables and provides
    default values where needed.
    """
    API_VERSION: str = "0.1.0"
    APP_NAME: str = "Snel API"
    APP_DESCRIPTION: str = "API for Snel DeFi Assistant"
    ENVIRONMENT: str = os.getenv("NODE_ENV", "development")
    
    # Services configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Security settings
    ALLOWED_ORIGINS: list = ["*"]  # CORS origins
    
    # Add all additional environment variables
    ALCHEMY_KEY: str = os.getenv("ALCHEMY_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ETH_RPC_URL: str = os.getenv("ETH_RPC_URL", "")
    OPTIMISM_RPC_URL: str = os.getenv("OPTIMISM_RPC_URL", "")
    POLYGON_RPC_URL: str = os.getenv("POLYGON_RPC_URL", "")
    ARBITRUM_RPC_URL: str = os.getenv("ARBITRUM_RPC_URL", "")
    BASE_RPC_URL: str = os.getenv("BASE_RPC_URL", "")
    SCROLL_RPC_URL: str = os.getenv("SCROLL_RPC_URL", "")
    QUICKNODE_ENDPOINT: str = os.getenv("QUICKNODE_ENDPOINT", "")
    COINGECKO_API_KEY: str = os.getenv("COINGECKO_API_KEY", "")
    MORALIS_API_KEY: str = os.getenv("MORALIS_API_KEY", "")
    ZEROX_API_KEY: str = os.getenv("ZEROX_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    QUICKNODE_API_KEY: str = os.getenv("QUICKNODE_API_KEY", "")
    DISABLE_SSL_VERIFY: str = os.getenv("DISABLE_SSL_VERIFY", "")
    BRIAN_API_KEY: str = os.getenv("BRIAN_API_KEY", "")
    BRIAN_API_URL: str = os.getenv("BRIAN_API_URL", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    PARTICLE_PROJECT_ID: str = os.getenv("PARTICLE_PROJECT_ID", "")
    PARTICLE_CLIENT_KEY: str = os.getenv("PARTICLE_CLIENT_KEY", "")
    PARTICLE_APP_ID: str = os.getenv("PARTICLE_APP_ID", "")
    MAIN_DOMAIN: str = os.getenv("MAIN_DOMAIN", "")
    TELEGRAM_WEBHOOK_PATH: str = os.getenv("TELEGRAM_WEBHOOK_PATH", "")
    
    class Config:
        """Pydantic config class."""
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in environment variables

# Create settings instance
settings = Settings() 