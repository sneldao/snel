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

# Initialize logger
configure_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Set up rate limiter
    limiter = Limiter(key_func=get_remote_address)
    app = FastAPI(
        title="Dowse Pointless API",
        description="API for Dowse Pointless, a crypto transaction assistant",
        version="1.0.0"
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add serverless compatibility middleware
    # Only apply in Vercel environment
    if os.environ.get("VERCEL", "0") == "1":
        try:
            from api.middleware import add_serverless_compatibility
            app = add_serverless_compatibility(app)
            logger.info("Added serverless compatibility middleware")
        except ImportError:
            logger.warning("Serverless compatibility middleware not found, skipping")
        except Exception as e:
            logger.error(f"Error adding serverless compatibility middleware: {e}")

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
    from app.api.routes import health, commands, transactions, swap_router
    app.include_router(health.router)
    app.include_router(commands.router)
    app.include_router(transactions.router)
    app.include_router(swap_router.router)

    # Add startup event
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
            openai_key = os.environ.get("OPENAI_API_KEY")

            if not all([alchemy_key, coingecko_key, moralis_key, openai_key]):
                missing_keys = []
                if not alchemy_key:
                    missing_keys.append("ALCHEMY_KEY")
                if not coingecko_key:
                    missing_keys.append("COINGECKO_API_KEY")
                if not moralis_key:
                    missing_keys.append("MORALIS_API_KEY")
                if not openai_key:
                    missing_keys.append("OPENAI_API_KEY")
                    
                logger.error(f"Missing required environment variables: {', '.join(missing_keys)}")
                raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")

            # Set Alchemy key for eth_rpc
            from eth_rpc import set_alchemy_key
            set_alchemy_key(alchemy_key)
            
            # Initialize token service
            from app.services.token_service import TokenService
            token_service = TokenService()
            
            # Initialize swap service
            from app.services.swap_service import SwapService
            from app.agents.swap_agent import SwapAgent
            from emp_agents.providers import OpenAIProvider
            
            provider = OpenAIProvider(api_key=openai_key)
            swap_agent = SwapAgent(provider=provider)
            swap_service = SwapService(token_service=token_service, swap_agent=swap_agent)
            
            # Store services in app state for dependency injection
            app.state.token_service = token_service
            app.state.swap_service = swap_service
            
            logger.info("Services initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    return app

# Create the FastAPI application
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
