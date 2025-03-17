"""
API routes for the application.
"""
from fastapi import APIRouter
from app.api.routes import ai, prices, swaps, messaging

# Create the main API router
api_router = APIRouter()

# Include the different route modules
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_router.include_router(prices.router, prefix="/prices", tags=["Prices"])
api_router.include_router(swaps.router, prefix="/swaps", tags=["Swaps"])
api_router.include_router(messaging.router, prefix="/messaging", tags=["Messaging"]) 