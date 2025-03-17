# Snel Telegram Bot

A Telegram bot for interacting with the Snel DeFi platform, featuring real wallet creation on Scroll Sepolia testnet.

## Features

- Real Ethereum wallet creation and management
- Token price checking
- Token swaps (testnet only)
- Balance checking
- Natural language processing

## Local Development

### Prerequisites

- Node.js 18+
- npm

### Setup

1. Clone the repository
2. Navigate to the telegram-bot directory
3. Install dependencies:
   ```
   npm install
   ```
4. Create a `.env` file with:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   API_URL=http://localhost:8000
   ```
5. Start the bot:
   ```
   npm run dev
   ```

## Vercel Deployment

### Prerequisites

- Vercel account
- Telegram bot token (from BotFather)

### Deployment Steps

1. Create a new Vercel project
2. Set the root directory to `telegram-bot`
3. Add the following environment variables:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `API_URL`: URL to your backend API (e.g., https://snel-pointless.vercel.app/api)
   - `NODE_ENV`: Set to "production"
4. Deploy the project

### Setting Up the Webhook

After deployment, you need to set up the webhook to receive updates from Telegram:

1. Make sure your Vercel project is deployed
2. Run the setup-webhook script:
   ```
   VERCEL_URL=your-vercel-url.vercel.app npm run setup-webhook
   ```
   Replace `your-vercel-url.vercel.app` with your actual Vercel URL

## Project Structure

- `src/index.js`: Main bot file and serverless function handler
- `src/wallet.js`: Wallet management functionality
- `src/api/webhook.js`: Webhook handler for Telegram updates
- `setup-webhook.js`: Script to set up the webhook
- `deploy.sh`: Deployment script
- `vercel.json`: Vercel configuration

## Troubleshooting

### Common Issues

#### Invalid Export Error

If you see "Invalid export found in module" error, make sure your `index.js` exports a function, not a bot instance:

```javascript
// Correct export for Vercel
export default async function handler(req, res) {
  // Function body
}
```

#### Webhook Not Working

1. Check if the webhook is set correctly:
   ```
   npm run setup-webhook
   ```
2. Make sure your Vercel URL is correct
3. Check Vercel logs for any errors

#### API Connection Issues

Make sure the `API_URL` environment variable is set correctly and points to your backend API.

## License

ISC
