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

// Export a serverless function
export default async function handler(req, res) {
  try {
    // Log information about the request
    console.log("[Webhook] Received request method:", req.method);
    console.log("[Webhook] Headers:", JSON.stringify(req.headers));
    console.log(
      "[Webhook] Body excerpt:",
      JSON.stringify(req.body).substring(0, 200)
    );

    if (req.method !== "POST") {
      return res.status(200).json({ ok: true, message: "Webhook is working" });
    }

    // Process the update with the bot
    await bot.handleUpdate(req.body);

    // Respond with 200 OK
    res.status(200).json({ ok: true });
  } catch (error) {
    console.error("[Webhook] Error in serverless function:", error);
    console.error(error.stack);
    res.status(500).json({ ok: false, error: error.message });
  }
}
