"""
Patches for Vercel deployment.
This file contains monkey patches for modules that need to be modified for Vercel deployment.
"""

import os
import ssl
import logging
import urllib3
import warnings

def patch_ssl_verification():
    """
    Patch SSL verification to handle issues in serverless environments.
    """
    # Disable SSL warnings when verification is disabled
    if os.environ.get("DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes"):
        warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)
        
        # Set default SSL context to unverified for requests
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
            logging.warning(
                "⚠️ SSL VERIFICATION DISABLED: This is insecure and should only be used in development."
            )
        except AttributeError:
            logging.warning("Failed to disable SSL verification")

def patch_dowse_logger():
    """
    Patch the Dowse logger to work in serverless environments.
    """
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO if os.environ.get("LOG_LEVEL") != "DEBUG" else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create a Dowse logger that will be used throughout the application
    logger = logging.getLogger("dowse")
    logger.setLevel(logging.INFO if os.environ.get("LOG_LEVEL") != "DEBUG" else logging.DEBUG)
    
    # Ensure the logger has at least one handler
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.info("Dowse logger configured for serverless environment")

def patch_dowse_modules():
    """
    Apply all needed patches for Vercel deployment.
    """
    patch_dowse_logger()
    patch_ssl_verification()
    
if __name__ == "__main__":
    patch_dowse_modules() 