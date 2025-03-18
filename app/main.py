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
    app.include_router(messaging_router_extended)  # Include at root level for direct access
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

# Add CDP diagnostic routes directly on the main app
@app.get("/api/cdp-debug")
async def cdp_debug_proxy():
    """Debug the CDP SDK configuration."""
    # Import needed modules
    import inspect
    import traceback
    import os
    
    try:
        # Import CDP components
        from cdp import Cdp, SmartWallet
        from eth_account import Account
        
        # Gather detailed information
        debug_info = {
            "cdp_info": {
                "module_path": getattr(Cdp, "__module__", "unknown"),
                "module_file": getattr(getattr(Cdp, "__module__", None), "__file__", "unknown"),
                "has_configure": hasattr(Cdp, "configure"),
                "has_use_server_signer": hasattr(Cdp, "use_server_signer"),
            },
            "smart_wallet_info": {
                "module_path": getattr(SmartWallet, "__module__", "unknown"),
                "has_create": hasattr(SmartWallet, "create"),
                "create_signature": str(inspect.signature(SmartWallet.create)) if hasattr(SmartWallet, "create") else "not found",
                "methods": [m for m in dir(SmartWallet) if not m.startswith("_")],
            },
            "environment": {
                "cdp_api_key_name": os.environ.get("CDP_API_KEY_NAME", "")[:5] + "..." if os.environ.get("CDP_API_KEY_NAME") else "missing",
                "cdp_api_key_private_key": "exists" if os.environ.get("CDP_API_KEY_PRIVATE_KEY") else "missing",
                "use_cdp_sdk": os.environ.get("USE_CDP_SDK", "false"),
                "cdp_use_managed_wallet": os.environ.get("CDP_USE_MANAGED_WALLET", "false"),
            }
        }
        
        # Try to create a test EOA
        try:
            test_eoa = Account.create()
            debug_info["eoa_test"] = {
                "address": test_eoa.address,
                "private_key_length": len(test_eoa.key.hex()) if hasattr(test_eoa, "key") else "unknown",
                "success": True
            }
        except Exception as eoa_err:
            debug_info["eoa_test"] = {
                "error": str(eoa_err),
                "traceback": traceback.format_exc(),
                "success": False
            }
        
        # Try to initialize the CDP SDK
        try:
            # Get API keys from environment
            api_key_name = os.getenv("CDP_API_KEY_NAME")
            api_key_private_key = os.getenv("CDP_API_KEY_PRIVATE_KEY")
            
            if api_key_name and api_key_private_key:
                # Configure the CDP SDK
                Cdp.configure(api_key_name, api_key_private_key)
                debug_info["cdp_initialize"] = {
                    "success": True,
                    "message": "CDP SDK initialized successfully"
                }
                
                # See if use_server_signer works
                try:
                    Cdp.use_server_signer = True
                    debug_info["cdp_initialize"]["server_signer"] = "enabled successfully"
                except Exception as ss_err:
                    debug_info["cdp_initialize"]["server_signer_error"] = str(ss_err)
            else:
                debug_info["cdp_initialize"] = {
                    "success": False,
                    "message": "API keys not available"
                }
        except Exception as cdp_err:
            debug_info["cdp_initialize"] = {
                "success": False,
                "error": str(cdp_err),
                "traceback": traceback.format_exc()
            }
            
        # Try to create a SmartWallet
        try:
            owner = Account.from_key(test_eoa.key)
            wallet = SmartWallet.create(account=owner)
            debug_info["wallet_create"] = {
                "success": True,
                "address": wallet.address if hasattr(wallet, "address") else "unknown",
                "wallet_repr": str(wallet),
                "wallet_dir": dir(wallet)
            }
        except Exception as wallet_err:
            debug_info["wallet_create"] = {
                "success": False,
                "error": str(wallet_err),
                "traceback": traceback.format_exc()
            }
            
        return debug_info
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
@app.post("/api/test-wallet-creation")
async def test_wallet_creation_proxy():
    """Test wallet creation endpoint."""
    import uuid
    from datetime import datetime
    import os
    
    try:
        from app.services.smart_wallet_service import SmartWalletService
        
        # Create a new instance of SmartWalletService
        wallet_service = SmartWalletService(redis_url=os.environ.get("REDIS_URL"))
        
        # Generate a unique test ID
        test_id = str(uuid.uuid4())[:8]
        
        # Try to create a wallet
        result = await wallet_service.create_smart_wallet(
            user_id=f"test-{test_id}",
            platform="test"
        )
        
        return {
            "success": True,
            "result": result,
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

@app.get("/api/check-wallet/{platform}/{user_id}")
async def check_wallet_for_user(platform: str, user_id: str):
    """Check wallet status for a specific user."""
    import os
    
    try:
        from app.services.smart_wallet_service import SmartWalletService
        
        # Create a new instance of SmartWalletService
        wallet_service = SmartWalletService(redis_url=os.environ.get("REDIS_URL"))
        
        # Get all possible wallet data
        wallet_keys = [
            f"wallet:{platform}:{user_id}",
            f"smart_wallet:{platform}:{user_id}",
            f"cdp_wallet:{platform}:{user_id}",
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
        
        # Try the actual get_smart_wallet method
        smart_wallet = await wallet_service.get_smart_wallet(user_id, platform)
        
        # Try wallet balance (don't fail if this fails)
        balance_data = None
        try:
            balance_data = await wallet_service.get_wallet_balance(user_id, platform, "base_sepolia")
        except Exception as balance_e:
            balance_data = {"error": str(balance_e)}
        
        return {
            "success": True,
            "wallet_data_in_redis": wallet_data,
            "get_smart_wallet_result": smart_wallet,
            "balance_check": balance_data,
            "cdp_initialized": wallet_service.cdp_initialized
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
        from app.services.smart_wallet_service import SmartWalletService
        from app.agents.telegram_agent import TelegramAgent
        from app.services.token_service import TokenService
        from app.services.swap_service import SwapService
        
        # Initialize required services
        redis_url = os.environ.get("REDIS_URL")
        wallet_service = SmartWalletService(redis_url=redis_url)
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
