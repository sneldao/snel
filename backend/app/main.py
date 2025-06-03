"""
FastAPI application entry point with centralized configuration and error handling.
"""
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import core components
from app.config.settings import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.dependencies import get_service_container

# Import API routers
from app.api.v1 import chat, swap, agno, health
from app.api.v1.websocket import router as websocket_router
from app.protocols.registry import protocol_registry

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.logging.level),
    format=settings.logging.format
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info(f"Starting SNEL API in {settings.environment} mode")

    # Initialize service container to validate configuration
    try:
        container = get_service_container(settings)
        logger.info("Service container initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize service container: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down SNEL API")
    try:
        await protocol_registry.close()
        await container.close()
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI application
app = FastAPI(
    title="SNEL API",
    description="API for SNEL - Cross-Chain Crypto Assistant",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan
)

# Configure CORS using settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
register_error_handlers(app)

# Include routers - unified architecture with chat endpoint handling all commands
app.include_router(health.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(swap.router, prefix="/api/v1")  # Legacy support for direct swap access
app.include_router(agno.router, prefix="/api/v1/agno")
app.include_router(websocket_router, prefix="/api/v1/ws")

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to SNEL API",
        "version": "1.0.0",
        "environment": settings.environment,
        "docs": "/docs",
        "health": "/api/v1/health"
    }


