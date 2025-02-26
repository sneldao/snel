"""
Test script to verify logger integration.
This script can be run to check if the Dowse logger patch is working correctly.
"""

import os
import sys
import logging
from pathlib import Path

def test_logger_integration():
    """Test if the Dowse logger patch is working correctly."""
    print("Starting logger integration test")
    
    # Set up Vercel environment flag for testing
    os.environ["VERCEL"] = "1"
    
    # Setup paths as in index.py
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add paths to Python path
    sys.path.insert(0, root_dir)  # Root directory first
    sys.path.insert(0, api_dir)   # API directory second
    
    # Import the patch function from index.py
    try:
        from api.index import patch_dowse_modules
        patch_result = patch_dowse_modules()
        print(f"Patch applied from index.py: {patch_result}")
    except Exception as e:
        print(f"Error applying patch from index.py: {e}")
    
    # Test direct import of Dowse logger
    try:
        import src.dowse.logger
        print("Successfully imported Dowse logger")
        print(f"Dowse logger handlers: {src.dowse.logger.logger.handlers}")
    except Exception as e:
        print(f"Error importing Dowse logger: {e}")
    
    # Test app configuration
    try:
        from app.utils.configure_logging import configure_logging
        app_logger = configure_logging()
        print(f"App logger configured: {app_logger}")
        app_logger.info("Test log message from app logger")
    except Exception as e:
        print(f"Error configuring app logger: {e}")
    
    # Test middleware
    try:
        from api.middleware import add_serverless_compatibility
        from fastapi import FastAPI
        app = FastAPI()
        app = add_serverless_compatibility(app)
        print("Middleware applied successfully")
    except Exception as e:
        print(f"Error applying middleware: {e}")
    
    print("Logger integration test completed")

if __name__ == "__main__":
    test_logger_integration() 