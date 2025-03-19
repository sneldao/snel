"""
Main application module.
"""
import logging
import os
from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.utils.configure_logging import configure_logging
from app.services.redis_service import get_redis_service, RedisService
from contextvars import ContextVar
import time
from dotenv import load_dotenv
import json
from fastapi.staticfiles import StaticFiles

# Load environment variables from .env files
load_dotenv()
load_dotenv(".env.local", override=True)  # Override with .env.local if it exists

# Make sure we have a default Redis URL if not provided in environment
if not os.environ.get("REDIS_URL"):
    redis_url = "redis://localhost:6379/0"
    os.environ["REDIS_URL"] = redis_url
    print(f"No REDIS_URL found, using default: {redis_url}")

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Set environment variables
environment = os.getenv("ENVIRONMENT", "production")
is_dev = environment == "development"

# Log important environment variables (without exposing sensitive values)
logger.info(f"Environment: {environment}")
logger.info(f"BRIAN_API_URL: {os.getenv('BRIAN_API_URL')}")
logger.info(f"BRIAN_API_KEY set: {bool(os.getenv('BRIAN_API_KEY'))}")

# Create FastAPI app
app = FastAPI(
    title="Pointless Snel API",
    description="API for the Pointless Snel app",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add error handler middleware
app.add_middleware(ErrorHandlerMiddleware)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ---------- BEGIN ROUTER CONFIGURATION ----------

# First include core command routes that are directly accessed by the frontend
from app.api.routes.commands_router import router as commands_router
app.include_router(commands_router, prefix="/api")  # /api/process-command endpoint

# Include swap router for frontend access
from app.api.routes.swap_router import router as swap_router
app.include_router(swap_router, prefix="/api/swap")  # /api/swap/process-command

# Include Telegram webhook handlers
from app.api.routes.messaging import router as messaging_router
app.include_router(messaging_router, prefix="/api/webhook")  # For compatibility
app.include_router(messaging_router, prefix="/api/telegram")  # For compatibility
app.include_router(messaging_router, prefix="/api/messaging/telegram")  # Fix for frontend Telegram access

# Include the messaging_router to handle Telegram webhook
try:
    # Import separately to avoid circular imports
    from app.api.routes.messaging_router import router as messaging_router_extended
    app.include_router(messaging_router_extended)  # Include at root level for direct access
    app.include_router(messaging_router_extended, prefix="/api/messaging")  # Main messaging routes
except (ImportError, AttributeError) as e:
    logger.warning(f"Could not import messaging_router_extended: {e}")

# Include the rest of the API routers
from app.api.routes.dca_router import router as dca_router
from app.api.routes.brian_router import router as brian_router
from app.api.routes.wallet_router import router as wallet_router
from app.api.routes.health import health_router

app.include_router(dca_router, prefix="/api/dca")
app.include_router(brian_router, prefix="/api/brian")
app.include_router(wallet_router, prefix="/api/wallet")
app.include_router(health_router, prefix="/api/health")

# Include wallet bridge routes
from app.api.routes.wallet_bridge import router as wallet_bridge_router
app.include_router(wallet_bridge_router)  # Already prefixed with /api/wallet-bridge

# ---------- END ROUTER CONFIGURATION ----------

# Add request ID middleware
request_id_contextvar = ContextVar("request_id", default=None)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Welcome to Snel Pointless API"}

@app.get("/api/check-wallet/{platform}/{user_id}")
async def check_wallet_for_user(platform: str, user_id: str):
    """Check wallet status for a specific user."""
    import os
    
    try:
        from app.services.wallet_service import WalletService
        
        # Create a new instance of WalletService
        redis_url = os.environ.get("REDIS_URL")
        wallet_service = WalletService(redis_service=RedisService(redis_url=redis_url) if redis_url else None)
        
        # Get all possible wallet data
        wallet_keys = [
            f"wallet:{platform}:{user_id}",
            f"messaging:{platform}:user:{user_id}:wallet"
        ]
        
        redis_client = wallet_service.redis_client
        if not redis_client:
            return {"error": "Redis client not available"}
        
        # Check all possible keys
        wallet_data = {}
        for key in wallet_keys:
            try:
                data = await redis_client.get(key)
                if data:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    try:
                        wallet_data[key] = json.loads(data)
                    except:
                        wallet_data[key] = data
            except Exception as e:
                wallet_data[key] = f"Error: {str(e)}"
        
        return {
            "success": True,
            "wallet_data_in_redis": wallet_data
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.post("/api/test-connect-command/{platform}/{user_id}")
async def test_connect_command(platform: str, user_id: str):
    """Test the connect command functionality for a user."""
    import os
    from datetime import datetime
    
    try:
        # Import components
        from app.services.wallet_service import WalletService 
        from app.agents.telegram_agent import TelegramAgent
        from app.services.token_service import TokenService
        from app.services.swap_service import SwapService
        
        # Initialize required services
        redis_url = os.environ.get("REDIS_URL")
        wallet_service = WalletService(redis_service=RedisService(redis_url=redis_url) if redis_url else None)
        token_service = TokenService()
        swap_service = SwapService(token_service=token_service, swap_agent=None)
        
        # Initialize the agent
        agent = TelegramAgent(
            token_service=token_service,
            swap_service=swap_service,
            wallet_service=wallet_service
        )
        
        # Call the connect command handler
        start_time = datetime.now()
        connect_result = await agent._handle_connect_command(user_id=user_id)
        end_time = datetime.now()
        
        # Get wallet status after connect command
        wallet_status = await check_wallet_for_user(platform, user_id)
        
        return {
            "success": True,
            "connect_command_result": connect_result,
            "wallet_status": wallet_status,
            "execution_time": (end_time - start_time).total_seconds(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=is_dev)
