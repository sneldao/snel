"""
Entry point for Vercel deployment.
This file is used by Vercel to run the application.
"""

import sys
import os
from pathlib import Path
import logging

# Setup paths
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
api_dir = os.path.dirname(os.path.abspath(__file__))

# Add paths to Python path
sys.path.insert(0, root_dir)  # Root directory first
sys.path.insert(0, api_dir)   # API directory second

# CRITICAL: Monkey patch Dowse's logging module BEFORE importing anything else
# This prevents the 'Read-only file system' error in serverless environments
def patch_dowse_modules():
    """
    Patch Dowse's logger module before it gets imported to prevent file system access.
    Must be called before any imports that might trigger Dowse's logger initialization.
    """
    import importlib.util
    import types
    import logging
    
    # Create a default logger that only writes to stdout
    logger = logging.getLogger("dowse")
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add a stdout handler only
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    
    # Create a fake logger module to replace dowse.logger
    # This prevents dowse from creating file handlers
    class MockLogger:
        def __init__(self, name="dowse"):
            self.name = name
            self.handlers = []
        
        def info(self, msg, *args, **kwargs):
            logger.info(msg, *args, **kwargs)
        
        def warning(self, msg, *args, **kwargs):
            logger.warning(msg, *args, **kwargs)
        
        def error(self, msg, *args, **kwargs):
            logger.error(msg, *args, **kwargs)
        
        def debug(self, msg, *args, **kwargs):
            logger.debug(msg, *args, **kwargs)
        
        def critical(self, msg, *args, **kwargs):
            logger.critical(msg, *args, **kwargs)
        
        def exception(self, msg, *args, **kwargs):
            logger.exception(msg, *args, **kwargs)
    
    # Create a fake module
    mock_logger_module = types.ModuleType("dowse.logger")
    mock_logger_module.logger = MockLogger()
    
    # Monkey patch sys.modules to include our fake module
    sys.modules["dowse.logger"] = mock_logger_module
    
    # Log that we've patched the module
    logger.info("Dowse logger monkey patched for serverless environment")
    return logger

# Apply the patch before importing anything from Dowse
patch_dowse_modules()

# Now it's safe to import the app
from app.main import app 