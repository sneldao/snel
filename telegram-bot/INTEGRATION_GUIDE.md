# Telegram Bot Integration Guide

This guide provides detailed information about integrating the SNEL Telegram bot with your FastAPI application.

## Overview

The Telegram integration allows users to interact with the SNEL AI Agent through Telegram, enabling features like:

- Token price checks
- Creating and managing wallets
- Swapping tokens
- Checking wallet balances
- Getting real-time crypto information
- Asking general questions about crypto and DeFi

## Prerequisites

Before you begin, ensure you have the following:

1. A Telegram bot token (created using @BotFather on Telegram)
2. Node.js installed (v18+)
3. The FastAPI backend running
4. ngrok or a similar tool for creating a public URL (for local development)

## Integration Architecture

The integration consists of the following components:

1. **FastAPI Webhook Endpoint** - Receives messages from Telegram
2. **Telegram Agent** - Processes messages and generates responses
3. **Setup Scripts** - Configure and verify the integration
4. **Environment Configuration** - Stores your bot token and API URLs

### FastAPI Webhook Endpoint

The webhook endpoint is defined in `app/api/routes/messaging_router.py` and processes incoming messages from Telegram. When a message is received, the endpoint:

1. Extracts the message content and user information
2. Forwards it to the Telegram agent for processing
3. Returns a 200 OK response to Telegram

The main webhook path is: `/api/messaging/telegram/webhook`

### Telegram Agent

The Telegram agent in `app/agents/telegram_agent.py` handles the processing of messages by:

1. Identifying commands and intents
2. Managing user sessions and wallet connections
3. Generating appropriate responses
4. Handling wallet operations like balance checks and swaps

## Setup Process

### Automated Setup

We provide a streamlined setup process using our `run.js` script:

```bash
cd telegram-bot
./run.js
```

This script will:

1. Check if your FastAPI server is running (and start it if needed)
2. Check if ngrok is running (and start it if needed)
3. Verify the Telegram integration
4. Set up the webhook automatically

### Manual Setup

If you prefer to set up the integration manually, follow these steps:

1. **Configure Environment Variables**

   Add your Telegram bot token to your `.env.local` file:

   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   ```

2. **Start the FastAPI Server**

   ```bash
   poetry run python server.py
   ```

3. **Create a Public URL with ngrok**

   ```bash
   ngrok http 8000
   ```

   Note the HTTPS URL provided by ngrok.

4. **Set Up the Webhook**

   ```bash
   cd telegram-bot
   node setup-webhook.js
   ```

   Or manually with curl:

   ```bash
   curl -X POST https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<YOUR_NGROK_DOMAIN>/api/messaging/telegram/webhook
   ```

5. **Verify the Integration**

   ```bash
   node verify-integration.js
   ```

## Testing

### Local Testing

You can test the webhook endpoint locally by sending a POST request:

```bash
curl -X POST http://localhost:8000/api/messaging/telegram/process \
  -H "Content-Type: application/json" \
  -d '{"platform":"telegram","user_id":"123456","message":"/start"}'
```

### Telegram Testing

Send messages directly to your bot on Telegram:

1. Start the bot with the `/start` command
2. Try `/help` to see available commands
3. Try natural language queries like "What's the price of ETH?"

## Troubleshooting

### Common Issues

1. **Webhook Not Set Up Correctly**

   - Check the webhook status: `curl -X GET https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
   - Ensure the URL is publicly accessible
   - Verify the webhook path matches your FastAPI endpoint

2. **Connection Issues**

   - Make sure ngrok is running
   - Check that your FastAPI server is running
   - Verify that your server responds to health checks

3. **Message Processing Issues**
   - Check the FastAPI server logs for errors
   - Verify that your Telegram bot token is correct
   - Ensure the Telegram agent is properly handling messages

### Logs

For debugging, check the following logs:

- FastAPI server logs for backend errors
- ngrok interface for webhook delivery issues
- Telegram bot logs via the BotFather interface

## Advanced Configuration

### Custom Commands

You can add custom commands to your Telegram bot:

1. Set up commands in BotFather using `/setcommands`
2. Add command handlers in `app/agents/telegram_agent.py`

### Message Formatting

Telegram supports various formatting options:

- Markdown: _italic_, **bold**, `code`, etc.
- HTML: <i>italic</i>, <b>bold</b>, <code>code</code>, etc.
- Inline buttons and keyboards

### Webhook Security

To enhance security:

1. Use HTTPS for your webhook URL
2. Consider adding a secret token to your webhook URL
3. Validate incoming requests

## Integration with Other Systems

The Telegram integration can be combined with:

- WhatsApp integration (similar webhook pattern)
- Web frontend (shared user data and wallet functionality)
- Mobile apps (through shared API endpoints)

## Resources

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [ngrok Documentation](https://ngrok.com/docs)
