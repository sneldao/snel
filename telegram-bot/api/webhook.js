import { Telegraf } from "telegraf";
import axios from "axios";

// Initialize the bot
const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN);

// Set API URL with fallback for production
const API_URL = process.env.API_URL || "https://snel-pointless.vercel.app/api";

// Function to create the request body for API calls
function createTelegramRequestBody(userId, message) {
  return {
    platform: "telegram",
    user_id: userId.toString(),
    message: message,
    metadata: {
      source: "telegram_bot",
      version: "1.0.0",
      timestamp: Date.now(),
    },
  };
}

// Handle messages
bot.on("text", async (ctx) => {
  try {
    const message = ctx.message.text;
    const userId = ctx.from.id.toString();

    console.log(`[Webhook] Received message from user ${userId}: ${message}`);

    // Forward to our dedicated Telegram endpoint
    const requestBody = createTelegramRequestBody(userId, message);
    console.log(
      `[Webhook] Sending to API: ${API_URL}/api/messaging/telegram/process`
    );

    const response = await axios.post(
      `${API_URL}/api/messaging/telegram/process`,
      requestBody,
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    console.log(`[Webhook] API response: ${JSON.stringify(response.data)}`);

    // Send the response back to the user
    await ctx.reply(response.data.content);
  } catch (error) {
    console.error(`[Webhook] Error processing message: ${error.message}`);

    // Send a friendly error message
    try {
      await ctx.reply(
        "Sorry, I encountered an error processing your request. Please try again later."
      );
    } catch (replyError) {
      console.error(
        `[Webhook] Could not send error message: ${replyError.message}`
      );
    }
  }
});

// Super simple webhook handler
export default function handler(req, res) {
  // Log request details
  console.log(`[${new Date().toISOString()}] Webhook received:`, {
    method: req.method,
    headers: req.headers,
    body: req.body ? JSON.stringify(req.body).substring(0, 200) : "No body",
    query: req.query,
  });

  // Always return 200 OK for Telegram
  res.status(200).json({ ok: true, message: "Webhook received" });
}
