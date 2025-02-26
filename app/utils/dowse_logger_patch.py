"""
Patch for Dowse logger to work in serverless environments.
"""

import logging
import os
import sys
from typing import Optional

def patch_dowse_logger() -> logging.Logger:
    """
    Patch the Dowse logger to work in serverless environments.
    
    Returns:
        A configured logger instance
    """
    # Configure root logger
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Create and configure app logger
    logger = logging.getLogger("app")
    logger.setLevel(getattr(logging, log_level))
    
    # Try to patch Dowse logger if it exists
    try:
        import dowse
        dowse_logger = logging.getLogger("dowse")
        dowse_logger.setLevel(getattr(logging, log_level))
        logger.info("Patched Dowse logger successfully")
    except ImportError:
        logger.warning("Dowse module not found, skipping Dowse logger patch")
    except Exception as e:
        logger.error(f"Failed to patch Dowse logger: {e}")
    
    # Disable file logging in serverless environments
    if os.environ.get("ENABLE_FILE_LOGGING", "false").lower() != "true":
        for handler in list(logger.handlers):
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)
                logger.info("Removed file handler from logger for serverless environment")
    
    return logger 