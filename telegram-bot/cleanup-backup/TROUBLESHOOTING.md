# Troubleshooting the Telegram Bot on Vercel

This guide provides solutions for common issues when deploying the Telegram bot to Vercel.

## Deployment Issues

### Bot Isn't Responding to Messages

1. **Check Vercel Logs**: Look for any errors in the Vercel deployment logs
2. **Verify Environment Variables**: Ensure `TELEGRAM_BOT_TOKEN` and `API_URL` are set correctly
3. **Check Bot Status**: Visit `https://your-vercel-app.vercel.app/status` to verify the bot is running
4. **Restart the Bot**: Redeploy the project on Vercel to restart the bot

### Dependency Issues

If you see errors about missing dependencies:

1. Make sure all necessary dependencies are in `package.json`
2. The bot now uses Telegraf instead of GrammY for better serverless compatibility
3. Run `npm install` locally to update your `package-lock.json` before deploying

### API Connection Issues

If the bot can't connect to your main API:

1. Verify the `API_URL` environment variable (should be `https://snel-pointless.vercel.app/api`)
2. Check that the `/api/messaging/telegram/process` endpoint is working on your main API
3. Test the API manually:
   ```
   curl -X POST "https://snel-pointless.vercel.app/api/messaging/telegram/process" \
     -H "Content-Type: application/json" \
     -d '{"platform":"telegram","user_id":"123456","message":"test","metadata":{"source":"telegram_bot"}}'
   ```

## Keeping the Bot Running on Vercel

Vercel's serverless functions shut down after periods of inactivity. Our solution:

1. We've implemented a keepalive mechanism that pings the bot every 5 minutes
2. For more reliable operation, consider upgrading to a paid Vercel plan

## Testing the Bot

1. Send a message to your bot on Telegram
2. Check Vercel logs for any errors or response information
3. If the bot doesn't respond, try sending the `/start` command
4. Verify the backend API is working by testing it directly

## Common Error Messages and Solutions

### "Cannot find module 'X'"

- This usually means a dependency is missing in package.json
- Make sure all dependencies are properly listed in package.json
- Try running `npm install` locally and redeploying

### "Bot Not Initialized"

- Redeploy the bot on Vercel
- Verify the `TELEGRAM_BOT_TOKEN` is correct

### "API Connection Failed"

- Check that your main API is running
- Verify the `API_URL` is correctly set to `https://snel-pointless.vercel.app/api`
- Ensure the `/api/messaging/telegram/process` endpoint is accepting requests

## Advanced Troubleshooting

For persistent issues:

1. Delete and recreate the Vercel project
2. Set up a new bot token with BotFather
3. Check for any IP restrictions on your API
4. Consider using a dedicated hosting solution rather than Vercel for more control
