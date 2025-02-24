import asyncio
import os
from dotenv import load_dotenv
import redis.asyncio as redis
import logging
import ssl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_redis_connection():
    try:
        # Get Redis URL from environment
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("REDIS_URL environment variable is not set")

        logger.info(f"Using Redis URL: {redis_url}")

        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Create Redis connection with SSL
        r = redis.from_url(
            redis_url.replace('redis://', 'rediss://'),  # Force SSL
            ssl=True,
            ssl_cert_reqs=None,  # Don't verify certificates
            decode_responses=True,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_timeout=5
        )

        # Test connection
        logger.info("Testing Redis connection...")
        await r.ping()
        logger.info("✅ Successfully connected to Redis")

        # Test basic operations
        test_key = "test_key"
        test_value = "test_value"

        # Set value
        logger.info("Testing SET operation...")
        await r.set(test_key, test_value, ex=1800)  # 30 minute TTL
        logger.info("✅ Successfully set value")

        # Get value
        logger.info("Testing GET operation...")
        retrieved_value = await r.get(test_key)
        if retrieved_value == test_value:
            logger.info("✅ Successfully retrieved value")
        else:
            logger.error(f"❌ Value mismatch. Expected: {test_value}, Got: {retrieved_value}")

        # Check TTL
        logger.info("Testing TTL...")
        ttl = await r.ttl(test_key)
        logger.info(f"✅ Key TTL: {ttl} seconds")

        # Delete key
        logger.info("Testing DELETE operation...")
        await r.delete(test_key)
        deleted_value = await r.get(test_key)
        if deleted_value is None:
            logger.info("✅ Successfully deleted key")
        else:
            logger.error("❌ Key was not deleted")

        # Close connection
        await r.close()
        logger.info("✅ All tests completed successfully!")

    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run tests
    asyncio.run(test_redis_connection()) 