// Minimal CommonJS version of the Telegram bot
require("dotenv").config();
const { Bot } = require("grammy");
const fetch = require("node-fetch");
const express = require("express");

// Constants
const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const API_URL = process.env.API_URL || "https://snel-pointless.vercel.app/api";

// Create bot
const bot = new Bot(TOKEN);

// Log startup info
console.log(`Starting minimal bot with API_URL: ${API_URL}`);
console.log(`Bot token: ${TOKEN ? TOKEN.substring(0, 5) + "..." : "Not set"}`);

// Simple command handling
bot.command("start", async (ctx) => {
  await ctx.reply(
    "👋 Welcome to Snel! I'm your DeFi assistant on Telegram.\n\n" +
      "I'm a Scroll-native multichain agent that can help you with various crypto tasks.\n\n" +
      "Try typing a message to get started, or visit our web app at https://snel-pointless.vercel.app/"
  );
});

bot.command("help", async (ctx) => {
  await ctx.reply(
    "I can help you with:\n\n" +
      "• Checking token prices\n" +
      "• Getting crypto information\n" +
      "• Learning about DeFi\n\n" +
      "Just type your question and I'll do my best to help!"
  );
});

// Handle all messages
bot.on("message", async (ctx) => {
  const message = ctx.message.text;
  if (!message) return;

  console.log(`Received message from user ${ctx.from.id}: ${message}`);

  try {
    // Forward to API
    const requestBody = {
      platform: "telegram",
      user_id: ctx.from.id.toString(),
      message: message,
      metadata: {
        source: "telegram_bot",
        version: "1.0.0",
        timestamp: Date.now(),
      },
    };

    console.log(
      `Sending to API endpoint: ${API_URL}/messaging/telegram/process`
    );

    const response = await fetch(`${API_URL}/messaging/telegram/process`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      throw new Error(`API responded with status: ${response.status}`);
    }

    const data = await response.json();
    console.log(`API response received`);

    // Send the response back to the user
    await ctx.reply(data.content || "Sorry, I couldn't process your request");
  } catch (error) {
    console.error(`Error processing message: ${error.message}`);

    await ctx.reply("Sorry, I encountered an error. Please try again later.");
  }
});

// Express app for health check
const app = express();

app.get("/", (req, res) => {
  res.json({
    status: "ok",
    bot: "running",
    timestamp: new Date().toISOString(),
  });
});

// Start bot with long polling
bot
  .start({
    drop_pending_updates: true,
    allowed_updates: ["message", "callback_query"],
  })
  .then(() => {
    console.log("Bot started with long polling");
  });

// Start Express server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Express server running on port ${PORT}`);
});

// Set up a keepalive mechanism
const PING_INTERVAL = 5 * 60 * 1000; // 5 minutes
setInterval(() => {
  console.log(`Keepalive ping at ${new Date().toISOString()}`);
  fetch(`https://${process.env.VERCEL_URL || "snel-telegram.vercel.app"}/`)
    .then((res) => {
      if (res.ok) {
        console.log("Keepalive ping successful");
      } else {
        console.error(`Keepalive failed with status: ${res.status}`);
      }
    })
    .catch((err) => {
      console.error("Keepalive ping failed:", err);
    });
}, PING_INTERVAL);

// Export for Vercel
module.exports = app;
