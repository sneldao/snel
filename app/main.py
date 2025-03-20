"""
Main application module.
"""
import logging
import os
from fastapi import FastAPI, Request, Response
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

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Set environment variables
environment = os.getenv("ENVIRONMENT", "production")
is_dev = environment == "development"
is_vercel = os.environ.get("VERCEL", "0") == "1"

# Log important environment variables (without exposing sensitive values)
logger.info(f"Environment: {environment}")
logger.info(f"Running on Vercel: {is_vercel}")

# Create FastAPI app
app = FastAPI(
    title="Pointless Snel API",
    description="API for the Pointless Snel app",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Add error handler middleware
app.add_middleware(ErrorHandlerMiddleware)

# Mount static files if not on Vercel (Vercel handles static files differently)
if not is_vercel:
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.exists(static_dir):
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
app.include_router(health_router)  # Health routes at root level for easier access

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

@app.get("/")
async def root():
    """Root endpoint that provides basic API information."""
    return {
        "status": "ok",
        "name": "Pointless Snel API",
        "version": "0.1.0",
        "environment": environment,
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=is_dev)
