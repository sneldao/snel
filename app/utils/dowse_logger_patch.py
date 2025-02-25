"""
Patch for the Dowse logger to make it compatible with serverless environments.
This file should be imported before any other Dowse imports.
"""

import logging
import os
import sys
from pathlib import Path

def patch_dowse_logger():
    """
    Patch the Dowse logger to use stdout only or the /tmp directory for log files.
    This makes it compatible with serverless environments like Vercel.
    """
    # Create a custom logger for Dowse
    logger = logging.getLogger("dowse")
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # Add stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
    
    # If we want to keep file logging, use the /tmp directory which is writable
    if os.environ.get("ENABLE_FILE_LOGGING", "").lower() == "true":
        log_path = Path("/tmp/dowse_info.log")
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
    
    # Monkey patch the dowse.logger module to use our logger
    try:
        import sys
        import dowse
        sys.modules["dowse.logger"] = type("LoggerModule", (), {"logger": logger})
        
        # Also patch the logger in the dowse module itself
        dowse.logger = logger
    except ImportError:
        # Dowse not installed yet, which is fine
        pass
    
    return logger 