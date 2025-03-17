# Snel Telegram Bot

A Telegram bot for interacting with the Snel DeFi assistant, providing wallet management, price checking, and token swaps on Scroll Sepolia testnet.

## Features

- 💰 Real Ethereum wallet creation and management
- 📊 Token price checking across chains
- 🔄 Token swaps with the best rates
- 💼 Balance checking for your wallet
- 🤖 Natural language processing for queries

## Local Development

### Prerequisites

- Node.js 18+
- npm
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   cd telegram-bot
   npm install
   ```
3. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
4. Update the `.env` file with your Telegram bot token and API URL
5. Start the bot in development mode:
   ```bash
   npm run dev
   ```

## Vercel Deployment

### Prerequisites

- A Vercel account
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))

### Deployment Steps

1. Push your code to a GitHub repository
2. Create a new project in Vercel
3. Connect your GitHub repository
4. Set the root directory to `telegram-bot`
5. Add the following environment variables:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `API_URL`: URL to your backend API (e.g., `https://your-api.vercel.app`)
   - `NODE_ENV`: Set to `production`
6. Deploy the project

### Setting Up the Webhook

After deploying to Vercel, you need to set up the webhook to receive updates from Telegram:

1. Add the `WEBHOOK_URL` environment variable to your Vercel project:

   - Format: `https://your-vercel-app.vercel.app/api/webhook`

2. Run the webhook setup script locally:

   ```bash
   # Install dependencies if you haven't already
   npm install

   # Set up the webhook
   TELEGRAM_BOT_TOKEN=your_bot_token WEBHOOK_URL=https://your-vercel-app.vercel.app/api/webhook node setup-webhook.js
   ```

3. Alternatively, you can set up the webhook directly from the Vercel console:
   - Go to your Vercel project
   - Open the "Functions" tab
   - Find and click on the "setup-webhook" function
   - Click "Run Function"

## Troubleshooting

### Invalid Export Error

If you see an error like `Cannot find module '/var/task/telegram-bot/node_modules/ws/wrapper.mjs'`, it's likely due to a dependency issue. Make sure your `package.json` doesn't include unnecessary dependencies like `ethers` that might cause conflicts.

### Webhook Issues

If your bot isn't receiving updates, check:

1. The webhook URL is correct and points to `/api/webhook`
2. The webhook is properly set up (run `node setup-webhook.js` again)
3. Check Vercel function logs for any errors

### API Connection Problems

If the bot can't connect to your API:

1. Verify the `API_URL` environment variable is correct
2. Ensure your API is running and accessible
3. Check CORS settings on your API if necessary

## Project Structure

- `src/index.js`: Main bot file with command handlers
- `src/wallet.js`: Wallet management functions
- `src/api/webhook.js`: Webhook handler for Telegram updates
- `setup-webhook.js`: Script to set up the Telegram webhook

## License

ISC
