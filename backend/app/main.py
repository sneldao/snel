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

from app.api.v1 import bridges, chat, swap, bridge, agno
from app.protocols.registry import protocol_registry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup: nothing to do
    yield
    # Shutdown: close all protocol clients
    await protocol_registry.close()

app = FastAPI(
    title="SNEL API",
    description="API for SNEL - Cross-Chain Crypto Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(_: Request, exc: Exception):
    logger.error(f"Error processing request: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Include routers - preserve original path structure for frontend compatibility
app.include_router(chat.router, prefix="/api/v1")
app.include_router(swap.router, prefix="/api/v1")
app.include_router(bridge.router, prefix="/api/v1")
app.include_router(bridges.router, prefix="/api/v1")
app.include_router(agno.router, prefix="/api/v1/agno")

@app.get("/")
async def root():
    return {"message": "Welcome to SNEL API. See /docs for API documentation."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
