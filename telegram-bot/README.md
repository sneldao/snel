# Snel Telegram Bot

Telegram bot integration for the Snel DeFi assistant

## Features

- Token price queries
- Wallet management
- Token swaps
- Balance checking

## Local Development

1. Install dependencies:

   ```
   npm install
   ```

2. Create a `.env` file with the following variables:

   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   API_URL=http://localhost:8000
   ```

3. Run the development server:
   ```
   npm run dev
   ```

## Deployment on Vercel

This bot is configured for deployment on Vercel using long polling:

1. Connect your GitHub repository to Vercel
2. Set the following environment variables in Vercel:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `API_URL`: URL of your backend API (e.g., https://snel-pointless.vercel.app/api)
   - `NODE_ENV`: Set to `production`
3. Deploy the project

## Endpoints

- `/`: Health check endpoint
- `/status`: Status endpoint showing bot info and configuration

## Important Notes

- The bot uses Telegraf framework for better compatibility with serverless environments
- Long polling is used instead of webhooks for reliability on Vercel
- In-memory session storage is used for user state management
- We use a keepalive mechanism to prevent Vercel from shutting down the function
- The bot communicates with the main API using the `/api/messaging/telegram/process` endpoint

## Architecture

- The bot acts as a middleware between Telegram and the Snel backend
- It formats messages appropriately and sends them to the backend for processing
- Session management is handled within the bot for a smoother user experience
- In production, the bot runs in a serverless function with a keepalive mechanism

## Troubleshooting

For deployment issues, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

## Setup

1. **Install Dependencies**

```bash
npm install
```

2. **Configure Environment Variables**

Create a `.env` file with the following variables:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
API_URL=http://localhost:8000
ENTRYPOINT_ADDRESS=0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789
FACTORY_ADDRESS=0x9406Cc6185a346906296840746125a0E44976454
CHAIN_ID=534352
RPC_URL=your_rpc_url
```

3. **Start the Bot**

```bash
npm start
```

For development with auto-reload:

```bash
npm run dev
```

## Usage

- `/start` - Start the bot
- `/help` - Show available commands
- `/connect` - Connect or create a wallet
- `/price [token]` - Check token price (e.g., `/price ETH`)
- `/swap [amount] [token] for [token]` - Create a swap (e.g., `/swap 0.1 ETH for USDC`)
- `/balance` - Check your wallet balance
- `/disconnect` - Disconnect your wallet

## Development Roadmap

- [x] MVP with basic functionality
- [ ] Real wallet creation with account abstraction
- [ ] Transaction execution with session keys
- [ ] Multi-chain support
- [ ] Advanced DeFi features (lending, staking, etc.)

## License

MIT
