"""
Test script for the wallet bridge functionality.
"""
import asyncio
import json
import os
from dotenv import load_dotenv
from app.services.wallet_bridge_service import WalletBridgeService

# Load environment variables
load_dotenv()
load_dotenv(".env.local", override=True)

async def test_wallet_bridge():
    """Test the wallet bridge functionality."""
    # Initialize the service
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    wallet_bridge_service = WalletBridgeService(redis_url=redis_url)
    
    # Test parameters
    test_user_id = "123456789"  # Example Telegram user ID
    test_connection_id = f"test_connection_{test_user_id}"
    test_wallet_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"  # Example wallet address
    
    # 1. Register a pending connection
    print("1. Registering a pending connection...")
    result = await wallet_bridge_service.register_pending_connection(
        connection_id=test_connection_id,
        user_id=test_user_id,
        platform="telegram"
    )
    print(f"Registration result: {json.dumps(result, indent=2)}")
    
    # 2. Get connection status
    print("\n2. Checking connection status...")
    status = await wallet_bridge_service.get_connection_status(test_connection_id)
    print(f"Connection status: {json.dumps(status, indent=2)}")
    
    # 3. Complete the connection
    print("\n3. Completing the connection with a wallet address...")
    completion = await wallet_bridge_service.complete_wallet_connection(
        connection_id=test_connection_id, 
        wallet_address=test_wallet_address
    )
    print(f"Completion result: {json.dumps(completion, indent=2)}")
    
    # 4. Get wallet info
    print("\n4. Getting wallet info for the user...")
    wallet_info = await wallet_bridge_service.get_wallet_info(
        user_id=test_user_id,
        platform="telegram"
    )
    print(f"Wallet info: {wallet_info}")
    
    # 5. Get wallet balance
    print("\n5. Getting wallet balance...")
    balance = await wallet_bridge_service.get_wallet_balance(
        user_id=test_user_id,
        platform="telegram",
        chain="base_sepolia"
    )
    print(f"Wallet balance: {json.dumps(balance, indent=2)}")
    
    print("\nWallet bridge test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_wallet_bridge()) 