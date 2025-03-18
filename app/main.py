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
logger.info(f"CDP_API_KEY_NAME set: {bool(os.getenv('CDP_API_KEY_NAME'))}")
logger.info(f"USE_CDP_SDK set: {os.getenv('USE_CDP_SDK')}")

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
    app.include_router(messaging_router_extended, prefix="/api/messaging")  # Main messaging routes
except (ImportError, AttributeError) as e:
    logger.warning(f"Could not import messaging_router_extended: {e}")

# Include the rest of the API routers
from app.api.routes.dca_router import router as dca_router
from app.api.routes.brian_router import router as brian_router
from app.api.routes.wallet_router import router as wallet_router

app.include_router(dca_router, prefix="/api/dca")
app.include_router(brian_router, prefix="/api/brian")
app.include_router(wallet_router, prefix="/api/wallet")

# Add health check router
try:
    from app.api.routes.health import router as health_router
    app.include_router(health_router, prefix="/api/health")
except ImportError:
    logger.warning("Health router not found, skipping.")

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
    return {"message": "Welcome to Dowse Pointless API"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=is_dev)
