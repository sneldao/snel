import asyncio
import os
import logging
import ssl
from dotenv import load_dotenv
from app.services.token_service import TokenService

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_ssl_configurations():
    """Test different SSL configurations."""
    
    # Test 1: Default configuration (with SSL verification)
    logger.info("Test 1: Default configuration (with SSL verification)")
    os.environ.pop("DISABLE_SSL_VERIFY", None)
    os.environ.pop("CA_CERT_PATH", None)
    
    token_service = TokenService()
    result = await token_service._lookup_token_quicknode("ETH", 1)
    logger.info(f"Default SSL config result: {result}")
    
    # Test 2: Disabled SSL verification
    logger.info("Test 2: Disabled SSL verification")
    os.environ["DISABLE_SSL_VERIFY"] = "true"
    os.environ.pop("CA_CERT_PATH", None)
    
    token_service = TokenService()
    result = await token_service._lookup_token_quicknode("ETH", 1)
    logger.info(f"Disabled SSL verification result: {result}")
    
    # Test 3: Custom CA certificates (if available)
    logger.info("Test 3: Custom CA certificates (if available)")
    os.environ.pop("DISABLE_SSL_VERIFY", None)
    
    # Check if we have a CA certificate file to test with
    ca_cert_path = "/etc/ssl/certs/ca-certificates.crt"  # Common location on Linux
    if os.path.exists(ca_cert_path):
        os.environ["CA_CERT_PATH"] = ca_cert_path
        
        token_service = TokenService()
        result = await token_service._lookup_token_quicknode("ETH", 1)
        logger.info(f"Custom CA certificates result: {result}")
    else:
        logger.warning(f"No CA certificate file found at {ca_cert_path}, skipping test")
    
    # Reset environment variables
    os.environ.pop("DISABLE_SSL_VERIFY", None)
    os.environ.pop("CA_CERT_PATH", None)

async def main():
    """Run the tests."""
    logger.info("Starting SSL configuration tests")
    await test_ssl_configurations()
    logger.info("Tests completed")

if __name__ == "__main__":
    asyncio.run(main()) 