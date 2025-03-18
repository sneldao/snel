# Coinbase CDP Wallet Integration

This guide explains how to use the Coinbase Developer Platform (CDP) for wallet functionality in your application.

## Overview

The Coinbase Developer Platform provides a robust SDK for creating and managing crypto wallets programmatically. This integration offers several advantages:

- Python native SDK (no JavaScript bridges needed)
- Developer-managed wallets (complete control)
- Smart wallet support (ERC-4337 compatible)
- Gas sponsoring via paymaster
- Batch transactions
- Official support from Coinbase

## Getting Started

### 1. Install Dependencies

Run the installation script to install all required dependencies:

```bash
./install-coinbase-deps.sh
```

### 2. Set Up Coinbase CDP API Keys

1. Create a Coinbase Developer Platform account at [https://www.coinbase.com/cloud](https://www.coinbase.com/cloud)
2. Create a new API key with appropriate permissions
3. Copy the API key name and private key to your `.env.local` file:

```
CDP_API_KEY_NAME=your_api_key_name
CDP_API_KEY_PRIVATE_KEY=your_api_key_private_key
```

### 3. Run the Test Script

Test if the integration works by running:

```bash
./test-coinbase-wallet.py
```

This will create a test wallet and verify connectivity with the Coinbase CDP.

## Implementation Details

This implementation provides two wallet service classes:

### 1. Basic Wallet Service (`CoinbaseWalletService`)

Located in `app/services/coinbase_wallet_service.py`, this service handles:

- Creating and managing EOA (Externally Owned Account) wallets
- Storing wallet information in Redis
- Retrieving wallet balances
- Basic wallet functions

### 2. Smart Wallet Service (`SmartWalletService`)

Located in `app/services/smart_wallet_service.py`, this service provides advanced functionality:

- ERC-4337 compatible smart wallets
- Gas sponsorship for transactions
- Batch transactions in a single operation
- Smart contract interactions
- Enhanced security features

## Security Considerations

The current implementation stores private keys in Redis as a demonstration. In a production environment:

1. You should encrypt all private keys before storage
2. Consider using Coinbase-Managed Wallets for enhanced security
3. Implement proper key rotation and recovery mechanisms
4. Add IP whitelisting for API key usage

## Telegram Bot Integration

To integrate with your Telegram bot:

1. Update your Telegram agent to use the new wallet services
2. Implement commands for wallet creation, balance checking, etc.
3. Create a user-friendly interface for wallet management

Example command implementation:

```python
# In your Telegram agent
from app.services.coinbase_wallet_service import CoinbaseWalletService
from app.services.smart_wallet_service import SmartWalletService

# Initialize services
wallet_service = CoinbaseWalletService(redis_url=os.getenv("REDIS_URL"))
smart_wallet_service = SmartWalletService(redis_url=os.getenv("REDIS_URL"))

# Connect wallet command
async def handle_connect_command(update, context):
    user_id = str(update.effective_user.id)
    wallet_data = await wallet_service.create_wallet(user_id, "telegram")

    if "error" in wallet_data:
        return f"Error creating wallet: {wallet_data['error']}"

    address = wallet_data.get("address")
    return f"Wallet created successfully! Your address: {address}"
```

## Testing on Testnet

By default, wallets are created on Base Sepolia testnet. To get testnet ETH:

1. Visit [https://faucet.base.org](https://faucet.base.org)
2. Enter your wallet address
3. Request testnet ETH

## Moving to Production

When moving to production:

1. Switch network to `base-mainnet` in wallet creation calls
2. Implement proper private key encryption
3. Set up monitoring for wallet activities
4. Consider implementing withdrawal limits and other safety measures
5. Add comprehensive error handling and recovery mechanisms

## Troubleshooting

Common issues:

- **API Key Errors**: Ensure your API keys are correctly set in the environment variables
- **Redis Connectivity**: Verify Redis connection URL is correct and Redis is running
- **Gas Errors**: Ensure your wallet has enough ETH for gas fees or implement proper paymaster
- **Transaction Failures**: Check error messages for specific issues with transactions

For more help, refer to the [Coinbase Developer Documentation](https://docs.developer.coinbase.com/).
