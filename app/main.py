from app.utils.configure_logging import configure_logging  # This must be the first import

import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Initialize logger
configure_logging()
logger = logging.getLogger(__name__)

# Set up rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://snel-pointless.vercel.app",
        "https://snel-pointless-git-main-papas-projects-5b188431.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api.routes import health, commands, transactions
app.include_router(health.router)
app.include_router(commands.router)
app.include_router(transactions.router)

# Initialize services
from app.services.redis_service import RedisService
from app.services.command_store import CommandStore
from app.services.token_service import TokenService
from eth_rpc import set_alchemy_key

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Log environment
    environment = os.environ.get("ENVIRONMENT", "production")
    logger.info(f"Starting API in {environment} environment")
    
    # Initialize services
    try:
        # Get environment variables
        alchemy_key = os.environ.get("ALCHEMY_KEY")
        coingecko_key = os.environ.get("COINGECKO_API_KEY")
        moralis_key = os.environ.get("MORALIS_API_KEY")

        if not all([alchemy_key, coingecko_key, moralis_key]):
            logger.error("Missing required environment variables")
            raise ValueError("Missing required environment variables")

        # Set Alchemy key
        set_alchemy_key(alchemy_key)
        
        # Test Redis connection
        redis_service = RedisService()
        command_store = CommandStore(redis_service)
        
        # Test Redis operations
        try:
            # Test Redis operations
            test_user_id = "test_user"
            test_command = "test_command"
            
            # Store test command
            command_store.store_command(test_user_id, test_command, chain_id=1)  # Use chain_id=1 for testing
            logger.info("Test command stored successfully")
            
            # Retrieve test command
            stored_command = command_store.get_command(test_user_id)
            if stored_command and stored_command["command"] == test_command:
                logger.info("Test command retrieved successfully")
            else:
                logger.error("Test command retrieval failed")
                
            # Clear test command
            command_store.clear_command(test_user_id)
            logger.info("Test command cleared successfully")
            
        except Exception as e:
            logger.error(f"Failed to test Redis connection: {e}")
            raise
            
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
