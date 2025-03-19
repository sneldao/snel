"""
Server bootstrap script for local development.
This file configures the environment and starts the FastAPI application.
"""

import os
import sys
import ssl
import logging
import warnings
import urllib3
from pathlib import Path
from dotenv import load_dotenv

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
logger.info("Starting Dowse Pointless server")

# Global flag to track if we've shown SSL warnings
SSL_WARNING_SHOWN = False

# Handle SSL certificate issues
if "SSL_CERT_FILE" in os.environ:
    # Check if the file exists
    cert_file = os.environ["SSL_CERT_FILE"]
    if not os.path.exists(cert_file):
        logger.warning(f"SSL_CERT_FILE was set to a non-existent path: {cert_file}")
        # Remove the environment variable to prevent errors
        os.environ.pop("SSL_CERT_FILE")
        SSL_WARNING_SHOWN = True

# Disable SSL verification if needed
if os.environ.get("DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes"):
    if not SSL_WARNING_SHOWN:
        logger.warning(
            "⚠️ SSL VERIFICATION DISABLED: This is insecure and should only be used in development."
        )
        SSL_WARNING_SHOWN = True
    
    # Disable SSL warnings
    warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)
    
    # Set default SSL context to unverified
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
    except AttributeError:
        logger.warning("Failed to disable SSL verification")

# Load environment variables
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

# Check for required environment variables
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# Check for wallet bridge required variables
if not os.getenv("WALLET_BRIDGE_URL"):
    logger.warning("WALLET_BRIDGE_URL is not set - wallet bridge functionality may be limited")

# Log important environment variables (without exposing sensitive values)
logger.info(f"BRIAN_API_URL: {os.getenv('BRIAN_API_URL')}")
logger.info(f"BRIAN_API_KEY set: {bool(os.getenv('BRIAN_API_KEY'))}")
logger.info(f"WALLET_BRIDGE_URL: {os.getenv('WALLET_BRIDGE_URL')}")

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
