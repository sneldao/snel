import asyncio
import os
from dotenv import load_dotenv
from api import RedisPendingCommandStore
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_redis_connection():
    try:
        # Initialize the command store
        store = RedisPendingCommandStore()
        await store.initialize()
        logger.info("✅ Successfully connected to Redis")

        # Test basic operations
        test_user = "test_user_123"
        test_command = "swap 1 ETH for USDC"
        test_chain_id = 8453  # Base chain

        # Store command
        logger.info("Testing command storage...")
        await store.store_command(test_user, test_command, test_chain_id)
        logger.info("✅ Successfully stored command")

        # Retrieve command
        logger.info("Testing command retrieval...")
        stored_command = await store.get_command(test_user)
        if stored_command and stored_command["command"] == test_command:
            logger.info("✅ Successfully retrieved command")
            logger.info(f"Retrieved data: {stored_command}")
        else:
            logger.error("❌ Command retrieval failed or data mismatch")
            logger.error(f"Expected: {test_command}")
            logger.error(f"Got: {stored_command}")

        # Test TTL
        logger.info("Testing TTL...")
        key = store._make_key(test_user)
        ttl = await store._redis.ttl(key)
        logger.info(f"✅ Command TTL: {ttl} seconds")

        # List all commands
        logger.info("Testing list all commands...")
        all_commands = await store.list_all_commands()
        logger.info(f"✅ All commands: {all_commands}")

        # Clear command
        logger.info("Testing command clearing...")
        await store.clear_command(test_user)
        cleared_command = await store.get_command(test_user)
        if cleared_command is None:
            logger.info("✅ Successfully cleared command")
        else:
            logger.error("❌ Command was not cleared")

    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Verify REDIS_URL is set
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is not set")
    
    # Run tests
    asyncio.run(test_redis_connection()) 