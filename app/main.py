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
logger.info(f"PARTICLE_PROJECT_ID set: {bool(os.getenv('PARTICLE_PROJECT_ID'))}")

# Create FastAPI app
app = FastAPI(
    title="Dowse Pointless API",
    description="API for the Dowse Pointless app",
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

# First include core routes directly
from app.api.routes.commands_router import router as commands_router
app.include_router(commands_router, prefix="/api")

# Then add webhook routes separately (since these are needed for compatibility)
from app.api.routes.messaging import router as webhook_router
app.include_router(webhook_router, prefix="/api/webhook")
app.include_router(webhook_router, prefix="/api/telegram")

# Finally include the rest of the API routes
from app.api.routes import api_router
app.include_router(api_router, prefix="/api")

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
