"""
Patch for Dowse logger to work in serverless environments.
"""

import logging
import os
import sys
import types
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
    
    # Direct monkey patch of sys.modules to ensure dowse.logger is properly patched
    # This handles cases where code directly imports from dowse.logger
    try:
        # Create a logger for dowse that only outputs to stdout
        dowse_logger = logging.getLogger("dowse")
        dowse_logger.setLevel(getattr(logging, log_level))
        
        # Clear handlers
        for handler in dowse_logger.handlers[:]:
            dowse_logger.removeHandler(handler)
        
        # Add stdout handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        dowse_logger.addHandler(handler)
        
        # Create a mock logger class
        class MockLogger:
            def __init__(self, name="dowse"):
                self.name = name
                self.handlers = [handler]
            
            def info(self, msg, *args, **kwargs):
                dowse_logger.info(msg, *args, **kwargs)
            
            def warning(self, msg, *args, **kwargs):
                dowse_logger.warning(msg, *args, **kwargs)
            
            def error(self, msg, *args, **kwargs):
                dowse_logger.error(msg, *args, **kwargs)
            
            def debug(self, msg, *args, **kwargs):
                dowse_logger.debug(msg, *args, **kwargs)
            
            def critical(self, msg, *args, **kwargs):
                dowse_logger.critical(msg, *args, **kwargs)
            
            def exception(self, msg, *args, **kwargs):
                dowse_logger.exception(msg, *args, **kwargs)
            
        # Create a fake module
        mock_logger_module = types.ModuleType("dowse.logger")
        mock_logger_module.logger = MockLogger()
        
        # Patch sys.modules
        sys.modules["dowse.logger"] = mock_logger_module
        
        logger.info("Patched dowse.logger in sys.modules")
    except Exception as e:
        logger.error(f"Error patching dowse.logger: {e}")
    
    # Disable file logging in serverless environments
    if os.environ.get("ENABLE_FILE_LOGGING", "false").lower() != "true":
        for handler in list(logger.handlers):
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)
                logger.info("Removed file handler from logger for serverless environment")
    
    return logger 