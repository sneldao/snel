"""
Main entry point for the application.
This file is used to run the application locally.
"""

import os
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Patch the Dowse logger before importing any Dowse modules
from app.utils.dowse_logger_patch import patch_dowse_logger
logger = patch_dowse_logger()
logger.info("Dowse logger patched successfully for local environment")

# Now it's safe to import the app
from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
