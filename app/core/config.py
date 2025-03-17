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
    
    class Config:
        """Pydantic config class."""
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings() 