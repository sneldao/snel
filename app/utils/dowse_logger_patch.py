"""
Patch for the Dowse logger to make it compatible with serverless environments.
This file should be imported before any other Dowse imports.
"""

import logging
import os
import sys as system_module  # Rename to avoid shadowing
from pathlib import Path
import importlib.util
import types

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
    handler = logging.StreamHandler(system_module.stdout)
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
    
    # Create a fake module to replace dowse.logger
    class LoggerModule(types.ModuleType):
        def __init__(self):
            super().__init__("dowse.logger")
            self.logger = logger
    
    # Create and install the fake module
    fake_logger_module = LoggerModule()
    system_module.modules["dowse.logger"] = fake_logger_module
    
    # If dowse is already imported, patch its logger attribute
    if "dowse" in system_module.modules:
        dowse_module = system_module.modules["dowse"]
        if hasattr(dowse_module, "logger"):
            dowse_module.logger = logger
    
    return logger 