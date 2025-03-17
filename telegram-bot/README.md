# Snel Telegram Bot

Telegram bot integration for the Snel DeFi assistant

## Current Architecture

The Telegram bot is now fully integrated with the main FastAPI backend. All bot functionality is handled directly by the main app at:

```
https://snel-pointless.vercel.app/api/messaging/telegram/webhook
```

## Features

- Webhook-based message handling
- Token price queries
- Wallet management with simulated addresses
- Token swaps with interactive buttons
- Balance checking
- Personality system with Snel's snail theme

## How It Works

1. The Telegram bot is configured to forward all messages to our webhook endpoint
2. The FastAPI app processes messages using a dedicated TelegramAgent
3. Responses are sent back to users via the Telegram Bot API
4. Interactive features like buttons and wallet connections are managed by the backend

## Bot Commands

- `/start` - Start the bot
- `/help` - Show available commands
- `/connect` - Connect or create a wallet
- `/price [token]` - Check token price (e.g., `/price ETH`)
- `/swap [amount] [token] for [token]` - Create a swap (e.g., `/swap 0.1 ETH for USDC`)
- `/balance` - Check your wallet balance
- `/disconnect` - Disconnect your wallet

## Development Roadmap

- [x] Integrated with main backend
- [x] Interactive buttons
- [x] Simulated wallet creation
- [ ] Real wallet creation with account abstraction
- [ ] Transaction execution with session keys
- [ ] Multi-chain support
- [ ] Advanced DeFi features (lending, staking, etc.)

## License

MIT
