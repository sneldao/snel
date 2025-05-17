"""
FastAPI application entry point.
"""
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from app.api.v1 import bridges, chat, swap
from app.protocols.manager import ProtocolManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create protocol manager instance
protocol_manager = ProtocolManager()

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup: nothing to do
    yield
    # Shutdown: close all protocol clients
    for protocol in protocol_manager.protocols.values():
        if hasattr(protocol, 'close'):
            await protocol.close()

app = FastAPI(
    title="Snel API",
    version="1.0.0",
    description="Backend API for Snel - Cross-chain bridging and token management",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://stable-snel.vercel.app",
        "https://stable-station.vercel.app",
    ],  # Configured for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(_: Request, exc: Exception):
    logger.error(f"Error processing request: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Include routers
app.include_router(bridges.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(swap.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
