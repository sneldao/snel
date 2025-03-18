"""
Main entry point for the application.
This file is used to run the application locally.
"""

import os
import sys
import logging
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.info("Starting Dowse Pointless application")

# Configure SSL verification for development
if os.getenv("DISABLE_SSL_VERIFY", "").lower() == "true":
    # Set a global environment variable to prevent duplicate warnings
    os.environ["SSL_WARNING_SHOWN"] = "true"
    
    # Display a more user-friendly warning
    logger.warning("⚠️ SECURITY WARNING: SSL certificate verification is disabled. This makes your connections less secure and should ONLY be used during development.")
    
    # Disable urllib3 warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)
env_local_path = Path(__file__).parent / '.env.local'
load_dotenv(env_local_path, override=True)  # Override with .env.local if it exists

# Log environment variable loading
logger.info(f"Loaded environment variables from {env_path}")
if env_local_path.exists():
    logger.info(f"Loaded environment variables from {env_local_path}")

# Validate required environment variables
required_vars = [
    "ALCHEMY_KEY",
    "COINGECKO_API_KEY",
    "MORALIS_API_KEY",
    "OPENAI_API_KEY",
    "BRIAN_API_KEY"  # Add Brian API key as required
]

# Check for CDP SDK if enabled
if os.getenv("USE_CDP_SDK", "").lower() in ["true", "1", "yes"]:
    logger.info("Coinbase CDP SDK is enabled, checking required variables")
    required_vars.extend([
        "CDP_API_KEY_NAME",
        "CDP_API_KEY_PRIVATE_KEY"
    ])

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# Log important environment variables (without exposing sensitive values)
logger.info(f"BRIAN_API_URL: {os.getenv('BRIAN_API_URL')}")
logger.info(f"BRIAN_API_KEY set: {bool(os.getenv('BRIAN_API_KEY'))}")
logger.info(f"CDP_USE_MANAGED_WALLET: {os.getenv('CDP_USE_MANAGED_WALLET')}")

# Import the app
from app.main import app

if __name__ == "__main__":
    import uvicorn
    
    # Configure uvicorn logging to match our format
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting server on port {port}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_config=log_config,
        log_level="info"
    )
