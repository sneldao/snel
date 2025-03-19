"""
Vercel handler for the Pointless API.
This file is the entry point for the Vercel serverless function.
"""

import sys
import os
from pathlib import Path

# Setup paths
root_dir = str(Path(__file__).parent.parent)
api_dir = str(Path(__file__).parent)

# Add paths to Python path
sys.path.insert(0, root_dir)  # Root directory first
sys.path.insert(0, api_dir)   # API directory second

# Import our patches module which will automatically apply the patches
from api.patches import patch_dowse_modules

# Apply the patches for Vercel deployment
patch_dowse_modules()

# Fix circular import issues by ensuring proper import order
try:
    # Import the models first to ensure they're loaded
    from app.models.telegram import TelegramMessage, TelegramWebhookRequest
    
    # Import dependencies in a specific order to avoid circular imports
    from app.services.redis_service import RedisService
    from app.services.token_service import TokenService
    from app.services.wallet_service import WalletService
    from app.services.smart_wallet_service import SmartWalletService
    
    # Now import the main app
    from app.main import app
except Exception as e:
    import logging
    import traceback
    logger = logging.getLogger("dowse")
    logger.error(f"Error importing modules: {e}")
    logger.error(traceback.format_exc())
    # Re-raise the exception
    raise 