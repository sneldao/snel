# Deploying the Telegram Bot to Vercel

This guide outlines how to deploy the Telegram bot to Vercel while ensuring it works alongside the existing backend.

## Pre-deployment Checklist

1. Make sure you have a valid Telegram bot token (create one via BotFather if needed)
2. Ensure your main application backend is deployed and accessible
3. Verify that the `/api/messaging/telegram/process` endpoint is working on your main application

## Deployment Steps

### 1. Create a New Project in Vercel

Create a new Vercel project specifically for the Telegram bot. This should be separate from your main application.

### 2. Connect to Your Repository

Connect Vercel to your GitHub repository. You may need to set up a specific branch or directory for the bot.

### 3. Configure Environment Variables

Add the following environment variables in your Vercel project settings:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `API_URL`: The URL of your main application API (e.g., `https://snel-pointless.vercel.app/api`)
- `NODE_ENV`: Set to `production`

### 4. Configure Build Settings

In the Vercel dashboard, set:

- Framework Preset: `Node.js`
- Root Directory: `telegram-bot` (if your bot is in a subdirectory)
- Build Command: `npm install`
- Output Directory: Leave blank
- Install Command: Leave as default
- Development Command: Leave blank

### 5. Deploy

Click "Deploy" in the Vercel dashboard. Once the deployment is complete, you'll get a URL for your bot.

### 6. Set Up Webhook

After deploying, you need to set up a webhook for your bot. Use the Telegram API to do this:

```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_VERCEL_URL>/webhook/<YOUR_BOT_TOKEN>
```

Replace:

- `<YOUR_BOT_TOKEN>` with your actual Telegram bot token
- `<YOUR_VERCEL_URL>` with the URL of your deployed bot (e.g., `https://your-bot-name.vercel.app`)

You can run this in your browser to set up the webhook.

### 7. Verify Deployment

To verify that your bot is running correctly:

1. Visit your bot's URL in a browser - you should see a health check response
2. Send a message to your bot on Telegram - it should respond correctly
3. Check the logs in your Vercel dashboard for any errors

## Troubleshooting

### Bot not responding

1. Verify that your environment variables are set correctly
2. Check that the webhook is set up properly
3. Examine the logs in the Vercel dashboard
4. Test the API endpoint (https://snel-pointless.vercel.app/api/messaging/telegram/process) directly
5. Ensure your Telegram bot token is valid

### Connection to API failing

1. Check that the API_URL is correct
2. Verify that your backend is running and the endpoint is accessible
3. Check CORS settings in your main application if needed
4. Test the API manually using a tool like Postman

### Deployment failing

1. Ensure your package.json has all required dependencies
2. Check that your vercel.json is correctly formatted
3. Verify that your index.js file is exporting the app correctly
4. Review the build logs in the Vercel dashboard
