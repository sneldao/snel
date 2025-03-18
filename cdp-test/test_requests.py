#!/usr/bin/env python3
"""
Simple test script to verify connectivity to Coinbase API endpoints using requests.
This script tests if we can access Coinbase APIs with or without SSL verification.
"""

import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("api-test")

def main():
    """Test connectivity to Coinbase API endpoints."""
    # Load environment variables
    load_dotenv("../.env")
    load_dotenv("../.env.local", override=True)
    
    # Check required environment variables
    api_key_name = os.getenv("CDP_API_KEY_NAME")
    
    if not api_key_name:
        logger.warning("CDP_API_KEY_NAME not found in environment variables. Testing with defaults.")
        api_key_name = "test"
    
    # Test endpoints
    endpoints = [
        "https://api.coinbase.com/v2/time",  # Public endpoint to test basic connectivity
        "https://api.wallet.coinbase.com/status",  # CDP status endpoint
    ]
    
    success = True
    
    for endpoint in endpoints:
        # First try with SSL verification
        try:
            logger.info(f"Testing endpoint with SSL verification: {endpoint}")
            response = requests.get(endpoint, timeout=10)
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response body: {response.text[:200]}...")
        except Exception as e:
            logger.error(f"Error accessing endpoint with SSL verification: {e}")
            success = False
        
        # Then try without SSL verification
        try:
            logger.info(f"Testing endpoint WITHOUT SSL verification: {endpoint}")
            response = requests.get(endpoint, verify=False, timeout=10)
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response body: {response.text[:200]}...")
        except Exception as e:
            logger.error(f"Error accessing endpoint without SSL verification: {e}")
            success = False
    
    # Test creating a connection to the CDP API
    try:
        logger.info("Testing CDP API authentication...")
        
        # Simple test to see if we can make a request with the environment variables
        # This isn't a real API endpoint but it will test if we have valid configuration
        base_url = "https://api.wallet.coinbase.com"
        endpoint = f"{base_url}/v1/management/wallets"
        
        # Try with and without SSL verification
        for verify in [True, False]:
            verification_status = "WITH" if verify else "WITHOUT"
            try:
                logger.info(f"Testing CDP endpoint {verification_status} SSL verification")
                
                # This is a simplified version, not the actual authentication
                headers = {
                    "X-Api-Key": api_key_name,
                    "Content-Type": "application/json"
                }
                
                response = requests.get(
                    endpoint, 
                    headers=headers,
                    verify=verify,
                    timeout=10
                )
                
                logger.info(f"Response status code: {response.status_code}")
                # We might get 401/403 which is fine as we're not fully authenticating
                if response.status_code in [401, 403]:
                    logger.info("Authentication required (expected)")
                else:
                    logger.info(f"Response body: {response.text[:200]}...")
            except Exception as e:
                logger.error(f"Error testing CDP endpoint {verification_status} SSL verification: {e}")
                success = False
    except Exception as e:
        logger.error(f"Error during CDP API test: {e}")
        success = False
    
    if success:
        logger.info("All tests completed - some succeeded!")
        return 0
    else:
        logger.warning("Some tests failed - check the logs for details")
        return 1

if __name__ == "__main__":
    # Disable SSL verification warnings for the test
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    sys.exit(main()) 