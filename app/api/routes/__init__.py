"""
API routes for the application.
"""
from fastapi import APIRouter

# Create the main API router
api_router = APIRouter()

# Import routers after creating api_router to avoid circular imports
from app.api.routes.commands_router import router as commands_router
from app.api.routes.swap_router import router as swap_router
from app.api.routes.dca_router import router as dca_router
from app.api.routes.brian_router import router as brian_router
from app.api.routes.wallet_router import router as wallet_router
from app.api.routes.messaging import router as messaging_router
from app.api.routes.messaging_router import router as messaging_router_extended
from app.api.routes.health import router as health_router

# Include the different route modules
api_router.include_router(commands_router, prefix="/commands", tags=["Commands"])
api_router.include_router(swap_router, prefix="/swaps", tags=["Swaps"])
api_router.include_router(dca_router, prefix="/dca", tags=["DCA"])
api_router.include_router(brian_router, prefix="/brian", tags=["Brian"])
api_router.include_router(wallet_router, prefix="/wallet", tags=["Wallet"])
api_router.include_router(messaging_router, prefix="/messaging", tags=["Messaging"])
api_router.include_router(messaging_router_extended, prefix="/messaging-extended", tags=["Messaging Extended"])
api_router.include_router(health_router, prefix="/health", tags=["Health"]) 