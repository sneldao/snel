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

// Super simple webhook handler - making this as minimal as possible for debugging
export default function handler(req, res) {
  // Log complete request details for debugging
  console.log(`[${new Date().toISOString()}] WEBHOOK RECEIVED:`, {
    method: req.method,
    path: req.url,
    headers: JSON.stringify(req.headers),
    body: req.body ? JSON.stringify(req.body) : "No body",
    query: req.query,
  });

  // Simplified for debugging - just respond with success and don't try to process
  // Always return 200 OK for Telegram
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    // Handle CORS preflight requests
    res.status(200).end();
    return;
  }

  try {
    if (req.body && req.body.message) {
      console.log("[WEBHOOK] Message received:", req.body.message);
    }
  } catch (error) {
    console.error("[WEBHOOK] Error processing message:", error);
  }

  // Just return success for now to debug the webhook connection
  res.status(200).json({ ok: true, message: "Webhook received" });
}
