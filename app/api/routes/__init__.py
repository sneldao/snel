# Routes package 
from app.api.routes.messaging_router import router as messaging_router
from app.api.routes.swap_router import router as swap_router
from app.api.routes.wallet_router import router as wallet_router
from app.api.routes.commands_router import router as commands_router
from app.api.routes.brian_router import router as brian_router
from app.api.routes.dca_router import router as dca_router
from app.api.routes.health import router as health_router

__all__ = [
    "messaging_router", 
    "swap_router", 
    "wallet_router",
    "commands_router",
    "brian_router",
    "dca_router",
    "health_router"
] 