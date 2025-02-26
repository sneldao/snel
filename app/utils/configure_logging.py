import logging
import os
import sys
from pathlib import Path

# Import the dowse logger patch
from app.utils.dowse_logger_patch import patch_dowse_logger

def configure_logging():
    """Configure logging for the application."""
    # Get log level from environment variable or default to INFO
    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Configure file handler if LOG_FILE is set
    log_file = os.environ.get("LOG_FILE")
    if log_file:
        # Check if we're in a serverless environment (Vercel)
        is_serverless = os.environ.get("VERCEL", "").lower() == "1"
        
        # If in serverless, use /tmp directory which is writable
        if is_serverless and not log_file.startswith("/tmp/"):
            log_file = f"/tmp/{os.path.basename(log_file)}"
            
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
            logging.getLogger().addHandler(file_handler)
            logging.getLogger(__name__).info(f"File logging enabled to: {log_file}")
        except (OSError, IOError) as e:
            logging.getLogger(__name__).warning(f"Could not set up file logging to {log_file}: {e}")
            logging.getLogger(__name__).info("Continuing with stdout logging only")
    
    # Set specific loggers to different levels if needed
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Apply the dowse logger patch
    patch_dowse_logger()
    
    # Create logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level_name}")
    
    return logger 