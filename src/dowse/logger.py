"""
Logger configuration for Dowse.
Serverless-friendly version that only logs to stdout.
"""

import logging
import os
import sys

# Create logger
logger = logging.getLogger("dowse")
logger.setLevel(logging.INFO)

# Clear any existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Add a stdout handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Only add file handler if explicitly enabled and not in a serverless environment
if (
    os.environ.get("ENABLE_FILE_LOGGING", "false").lower() == "true" and
    os.environ.get("VERCEL", "0") != "1"
):
    try:
        # Use /tmp directory in serverless environments if file logging is forced
        log_dir = "/tmp" if os.environ.get("VERCEL", "0") == "1" else "."
        log_path = os.path.join(log_dir, "dowse_info.log")
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"File logging enabled at {log_path}")
    except Exception as e:
        logger.warning(f"Failed to set up file logging: {e}")
else:
    logger.info("File logging disabled")

# Log startup info
logger.info("Dowse logger initialized")
