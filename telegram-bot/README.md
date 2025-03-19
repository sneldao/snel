# Telegram Bot Integration

This directory contains tools for integrating Telegram with your main Pointless Snel app.

## Prerequisites

1. A Telegram bot token from [@BotFather](https://t.me/botfather)
2. ngrok or a similar tool for exposing your local server
3. Node.js 16+ and npm

## Setup

1. Install dependencies:

```bash
npm install
```

2. Copy the `.env.example` file to `.env` and fill in your Telegram bot token:

```bash
cp .env.example .env
# Edit the .env file and add your Telegram bot token
```

## Integration with Main App

The Telegram bot integration works with your main FastAPI app. Here's how to set it up:

### Step 1: Make sure your FastAPI app is running

```bash
# In your main app directory
uvicorn app.main:app --reload
```

### Step 2: Start ngrok to expose your local server

```bash
ngrok http 8000
```

Note the HTTPS URL that ngrok gives you (e.g., `https://abc123.ngrok-free.app`).

### Step 3: Verify that your FastAPI app is properly configured for Telegram

```bash
# Test the Telegram integration
node verify-integration.js
```

This script sends test requests to your FastAPI app to verify that the Telegram webhook endpoints are working correctly.

### Step 4: Set up the Telegram webhook

```bash
# Automatically detect ngrok URL and set the webhook
node setup-webhook.js
```

This script automatically detects your ngrok URL and configures your Telegram bot to use it for webhooks.

### Step 5: Test the bot

Send a message to your Telegram bot to verify that everything is working correctly.

## Available Scripts

- `test-bot.js` - Test basic Telegram bot connectivity
- `setup-webhook.js` - Automatically detect ngrok URL and set up webhook
- `webhook-manager.js` - Manage Telegram webhooks (set, info, delete)
- `verify-integration.js` - Test the FastAPI Telegram integration
- `local-webhook-server.js` - Run a local webhook server for testing (not needed with FastAPI integration)

## Troubleshooting

### Webhook not receiving messages

1. Check that your ngrok URL is correct and that the tunnel is still active
2. Verify that your FastAPI app is running
3. Check webhook info: `node webhook-manager.js info`
4. Look at your FastAPI logs for any errors

### Bot not responding

1. Make sure your FastAPI app is correctly processing Telegram messages
2. Check that your Telegram bot token is correct
3. Verify that the bot is activated (try sending `/start` to it)
4. Check the environment variables in your FastAPI app

## Production Deployment

For production, you'll need to set up a permanent webhook URL:

1. Deploy your FastAPI app to a cloud provider
2. Use your production domain instead of ngrok
3. Set up the webhook using the production URL:

```bash
node webhook-manager.js set https://your-production-domain.com/api/messaging/telegram/webhook
```

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
