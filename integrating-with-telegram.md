# Integrating Coinbase CDP Wallet with Telegram Bot

This guide explains how to integrate the Coinbase CDP wallet functionality with your existing Telegram bot.

## Prerequisites

1. Working Telegram bot set up
2. Coinbase Developer Platform API keys
3. Redis instance for data persistence

## Integration Steps

### 1. Update Your Dependencies

Make sure you have the required dependencies:

```bash
# If using pip
pip install cdp-sdk eth-account web3 python-dotenv redis

# If using Poetry (recommended)
poetry add cdp-sdk eth-account web3 python-dotenv redis
```

### 2. Update Your Environment Variables

Add these to your `.env.local` file:

```
# Coinbase Developer Platform credentials
CDP_API_KEY_NAME=your_api_key_name
CDP_API_KEY_PRIVATE_KEY=your_api_key_private_key
```

### 3. Update the Telegram Agent to Use Coinbase Wallet

Update your `app/agents/telegram_agent.py` file to use the new wallet service:

```python
from app.services.smart_wallet_service import SmartWalletService

class TelegramAgent:
    def __init__(self, redis_url=None):
        # Initialize other services...

        # Initialize the Smart Wallet Service
        self.wallet_service = SmartWalletService(redis_url=redis_url)
```

### 4. Add Wallet Commands to Your Telegram Bot

Update your command handlers to use the Smart Wallet Service:

```python
async def _handle_connect_command(self, user_id, args=None, wallet_address=None):
    """Handle the /connect command to create a new smart wallet."""
    try:
        # Create a smart wallet for the user
        wallet_data = await self.wallet_service.create_smart_wallet(user_id, platform="telegram")

        if "error" in wallet_data:
            return f"❌ Failed to create wallet: {wallet_data['error']}"

        address = wallet_data.get("address")
        return f"✅ Wallet created successfully!\n\nYour address: `{address}`\n\nNetwork: Base Sepolia (testnet)\n\nGet test ETH from: https://faucet.base.org"

    except Exception as e:
        logger.exception(f"Error handling connect command: {e}")
        return "❌ Failed to create wallet. Please try again later."

async def _handle_balance_command(self, user_id, args=None, wallet_address=None):
    """Handle the /balance command to check wallet balance."""
    try:
        # Get the user's wallet balance
        balance_data = await self.wallet_service.get_wallet_balance(user_id, platform="telegram")

        if "error" in balance_data:
            return f"❌ Failed to get balance: {balance_data['error']}"

        address = balance_data.get("address")
        eth_balance = balance_data.get("balance", {}).get("eth", "0.0")

        return f"💰 Wallet Balance\n\nAddress: `{address}`\nETH: {eth_balance}\nNetwork: Base Sepolia (testnet)"

    except Exception as e:
        logger.exception(f"Error handling balance command: {e}")
        return "❌ Failed to get balance. Please try again later."

async def _handle_faucet_command(self, user_id, args=None, wallet_address=None):
    """Handle the /faucet command to get testnet ETH."""
    try:
        # Get faucet instructions
        faucet_data = await self.wallet_service.fund_wallet_from_faucet(user_id, platform="telegram")

        if not faucet_data.get("success", False):
            return f"❌ Failed to get faucet instructions: {faucet_data.get('message', 'Unknown error')}"

        address = faucet_data.get("address")
        faucet_url = faucet_data.get("faucet_url")

        return f"🚰 Faucet Instructions\n\nTo get test ETH, visit: {faucet_url}\n\nEnter your wallet address: `{address}`\n\nThis will give you test ETH to experiment with."

    except Exception as e:
        logger.exception(f"Error handling faucet command: {e}")
        return "❌ Failed to get faucet instructions. Please try again later."
```

### 5. Update Bot Command Descriptions

Update your command list in BotFather:

```
connect - Create a new wallet powered by Coinbase
balance - Check your wallet balance
faucet - Get instructions to get test ETH
send - Send ETH to another address
help - Show available commands
```

### 6. Add Transaction Command

```python
async def _handle_send_command(self, user_id, args=None, wallet_address=None):
    """Handle the /send command to send ETH."""
    if not args:
        return "❌ Please specify an address and amount. Example: `/send 0x123... 0.01`"

    try:
        # Parse arguments
        parts = args.split()
        if len(parts) < 2:
            return "❌ Please specify both an address and amount. Example: `/send 0x123... 0.01`"

        to_address = parts[0]
        try:
            amount = float(parts[1])
        except ValueError:
            return "❌ Invalid amount. Please specify a number. Example: `/send 0x123... 0.01`"

        # Send transaction
        tx_data = await self.wallet_service.send_transaction(user_id, "telegram", to_address, amount)

        if not tx_data.get("success", False):
            return f"❌ Failed to send transaction: {tx_data.get('message', 'Unknown error')}"

        tx_hash = tx_data.get("tx_hash")

        return f"✅ Transaction sent successfully!\n\nAmount: {amount} ETH\nTo: `{to_address}`\nTransaction hash: `{tx_hash}`\n\nNetwork: Base Sepolia (testnet)"

    except Exception as e:
        logger.exception(f"Error handling send command: {e}")
        return "❌ Failed to send transaction. Please try again later."
```

### 7. Add Batch Transaction Support (Optional)

For advanced users, you can add support for batch transactions:

```python
async def _handle_batch_command(self, user_id, args=None, wallet_address=None):
    """Handle the /batch command to send multiple transactions."""
    # Implementation details would go here
    # This would use smart_wallet_service.batch_transactions()
    pass
```

## Testing the Integration

To test your integration:

1. Start your Telegram bot
2. Use the `/connect` command to create a new wallet
3. Use the `/faucet` command to get instructions for getting test ETH
4. Use the `/balance` command to check your wallet balance
5. Try sending a small amount of ETH using the `/send` command

## Troubleshooting

Common issues:

- **"CDP API keys not found"**: Make sure your CDP API keys are correctly set in the environment variables
- **"Failed to create wallet"**: Check your Redis connection and make sure the CDP SDK is correctly installed
- **"Failed to send transaction"**: Ensure your wallet has enough ETH for gas fees
