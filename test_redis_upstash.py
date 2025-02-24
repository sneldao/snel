import os
from dotenv import load_dotenv
from upstash_redis import Redis
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_redis_url(url):
    """Parse Redis URL to get Upstash REST URL and token."""
    parsed = urlparse(url)
    
    # Extract the hostname (e.g., touched-crab-18970.upstash.io)
    hostname = parsed.hostname
    
    # Construct the REST URL
    rest_url = f"https://{hostname}"
    
    # Get the token (password) from the URL
    token = parsed.password
    
    return rest_url, token

def test_redis_connection():
    try:
        # Get Redis URL from environment
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("REDIS_URL environment variable is not set")

        logger.info(f"Using Redis URL: {redis_url}")

        # Parse Redis URL to get REST URL and token
        rest_url, token = parse_redis_url(redis_url)
        logger.info(f"Parsed REST URL: {rest_url}")

        # Create Redis connection
        redis = Redis(
            url=rest_url,
            token=token
        )

        # Test connection
        logger.info("Testing Redis connection...")
        ping_result = redis.ping()
        if ping_result:
            logger.info("✅ Successfully connected to Redis")
        else:
            logger.error("❌ Redis ping failed")
            return

        # Test basic operations
        test_key = "test_key"
        test_value = "test_value"

        # Set value
        logger.info("Testing SET operation...")
        set_result = redis.set(test_key, test_value, ex=1800)  # 30 minute TTL
        if set_result:
            logger.info("✅ Successfully set value")
        else:
            logger.error("❌ Failed to set value")
            return

        # Get value
        logger.info("Testing GET operation...")
        retrieved_value = redis.get(test_key)
        if retrieved_value == test_value:
            logger.info("✅ Successfully retrieved value")
        else:
            logger.error(f"❌ Value mismatch. Expected: {test_value}, Got: {retrieved_value}")
            return

        # Check TTL
        logger.info("Testing TTL...")
        ttl = redis.ttl(test_key)
        logger.info(f"✅ Key TTL: {ttl} seconds")

        # Delete key
        logger.info("Testing DELETE operation...")
        delete_result = redis.delete(test_key)
        if delete_result:
            logger.info("✅ Successfully deleted key")
        else:
            logger.error("❌ Failed to delete key")
            return

        # Verify deletion
        deleted_value = redis.get(test_key)
        if deleted_value is None:
            logger.info("✅ Verified key was deleted")
        else:
            logger.error("❌ Key still exists after deletion")
            return

        logger.info("✅ All tests completed successfully!")

    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run tests
    test_redis_connection() 