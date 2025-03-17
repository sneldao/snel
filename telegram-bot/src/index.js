// Load polyfills and environment
import "whatwg-url";
import "web-streams-polyfill";
import "abortcontroller-polyfill/dist/abortcontroller-polyfill-only.js";
import "formdata-polyfill";
import "dotenv/config";

import { Bot, InlineKeyboard, session } from "grammy";
import fetch from "node-fetch";
import {
  generateWalletAddress,
  storeWalletInfo,
  getWalletInfo,
  getWalletBalance,
} from "./wallet.js";

// Set API URL with fallback for production
const API_URL = process.env.API_URL || "https://snel-pointless.vercel.app/api";

// Initialize the bot
const bot = new Bot(process.env.TELEGRAM_BOT_TOKEN);

// Log startup information
console.log(`Starting bot with API_URL: ${API_URL}`);
console.log(
  `Webhook URL should be set to: https://[your-vercel-domain]/webhook`
);

// Middleware for session management
bot.use(
  session({
    initial: () => ({
      walletAddress: null,
      pendingSwap: null,
    }),
  })
);

// Command handlers
bot.command("start", async (ctx) => {
  await ctx.reply(
    "👋 Welcome to Snel! I'm your DeFi assistant on Telegram.\n\n" +
      "I'm a Scroll-native multichain agent that can help you with:\n" +
      "• Checking token prices\n" +
      "• Swapping tokens across chains\n" +
      "• Managing your wallet\n" +
      "• Executing transactions\n\n" +
      "Try /help to see available commands, or visit our web app at https://snel-pointless.vercel.app/\n\n" +
      "🐌 I might be slow, but I'll get you there safely!"
  );
});

bot.command("help", async (ctx) => {
  await ctx.reply(
    "🔍 Here's what I can do:\n\n" +
      "/connect - Connect or create a wallet\n" +
      "/price [token] - Check token price (e.g., /price ETH)\n" +
      "/swap [amount] [token] for [token] - Create a swap (e.g., /swap 0.1 ETH for USDC)\n" +
      "/balance - Check your wallet balance\n" +
      "/disconnect - Disconnect your wallet\n\n" +
      "I'm still learning, so please be patient with me! 🐌"
  );
});

// Connect wallet command
bot.command("connect", async (ctx) => {
  // Check if user already has a wallet
  const userId = ctx.from.id.toString();
  const existingWallet = getWalletInfo(userId);

  if (existingWallet && ctx.session.walletAddress) {
    return ctx.reply(
      `You already have a wallet connected!\n\n` +
        `Address: ${ctx.session.walletAddress}\n\n` +
        `Use /disconnect if you want to disconnect this wallet.`
    );
  }

  // For MVP, we'll simulate wallet creation
  const keyboard = new InlineKeyboard()
    .text("Create New Wallet", "create_wallet")
    .text("Connect Existing", "connect_existing");

  await ctx.reply(
    "Let's set up your wallet. You can create a new wallet or connect an existing one:",
    { reply_markup: keyboard }
  );
});

// Balance command
bot.command("balance", async (ctx) => {
  const userId = ctx.from.id.toString();

  // Check if user has a wallet
  if (!ctx.session.walletAddress) {
    const walletAddress = getWalletInfo(userId);

    if (walletAddress) {
      ctx.session.walletAddress = walletAddress;
    } else {
      return ctx.reply(
        "You don't have a wallet connected yet. Use /connect to set up your wallet."
      );
    }
  }

  // Get wallet balance
  const balance = getWalletBalance(ctx.session.walletAddress);

  await ctx.reply(
    `Your wallet balance:\n\n` +
      `ETH: ${balance.eth}\n` +
      `USDC: ${balance.usdc}\n` +
      `USDT: ${balance.usdt}\n` +
      `DAI: ${balance.dai}\n\n` +
      `Wallet: ${ctx.session.walletAddress.substring(
        0,
        6
      )}...${ctx.session.walletAddress.substring(38)}`
  );
});

// Disconnect command
bot.command("disconnect", async (ctx) => {
  if (!ctx.session.walletAddress) {
    return ctx.reply("You don't have a wallet connected.");
  }

  const walletAddress = ctx.session.walletAddress;
  ctx.session.walletAddress = null;

  await ctx.reply(
    `Wallet disconnected: ${walletAddress.substring(
      0,
      6
    )}...${walletAddress.substring(38)}`
  );
});

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

// Price command
bot.command("price", async (ctx) => {
  const message = ctx.message.text;
  const parts = message.split(" ");

  if (parts.length < 2) {
    return ctx.reply("Please specify a token. Example: /price ETH");
  }

  const token = parts[1].toUpperCase();

  // Use the dedicated Telegram endpoint
  try {
    const response = await fetch(`${API_URL}/api/messaging/telegram/process`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(
        createTelegramRequestBody(ctx.from.id, `price of ${token}`)
      ),
    });

    const data = await response.json();
    await ctx.reply(data.content);
  } catch (error) {
    console.error("Error fetching price:", error);
    await ctx.reply(
      `Sorry, I couldn't get the price of ${token}. Please try again later.`
    );
  }
});

// Swap command
bot.command("swap", async (ctx) => {
  const userId = ctx.from.id.toString();

  // Check if user has a wallet
  if (!ctx.session.walletAddress) {
    const walletAddress = getWalletInfo(userId);

    if (walletAddress) {
      ctx.session.walletAddress = walletAddress;
    } else {
      return ctx.reply(
        "You need to connect a wallet first. Use /connect to set up your wallet."
      );
    }
  }

  const message = ctx.message.text;

  // Skip the /swap part
  const swapText = message.substring(6).trim();

  if (!swapText) {
    return ctx.reply(
      "Please specify the swap details. Example: /swap 0.1 ETH for USDC"
    );
  }

  // Parse the swap text
  const swapMatch = swapText.match(/(\d+\.?\d*)\s+(\w+)\s+(?:to|for)\s+(\w+)/i);

  if (!swapMatch) {
    return ctx.reply(
      "I couldn't understand your swap request. Please use the format:\n" +
        "/swap [amount] [token] for [token]\n\n" +
        "Example: /swap 0.1 ETH for USDC"
    );
  }

  const [_, amount, fromToken, toToken] = swapMatch;

  // For MVP, we'll simulate getting a quote
  const estimatedOutput = (
    parseFloat(amount) *
    (Math.random() * 0.2 + 0.9) *
    1800
  ).toFixed(2);

  const keyboard = new InlineKeyboard()
    .text("Approve Swap", "approve_swap")
    .text("Cancel", "cancel_swap");

  // Store the swap request in session
  ctx.session.pendingSwap = {
    fromToken: fromToken.toUpperCase(),
    toToken: toToken.toUpperCase(),
    amount: parseFloat(amount),
    estimatedOutput: parseFloat(estimatedOutput),
    timestamp: Date.now(),
  };

  await ctx.reply(
    `Swap Quote:\n\n` +
      `From: ${amount} ${fromToken.toUpperCase()}\n` +
      `To: ~${estimatedOutput} ${toToken.toUpperCase()}\n` +
      `Fee: 0.3%\n\n` +
      `Do you want to proceed with this swap?`,
    { reply_markup: keyboard }
  );
});

// Handle callback queries
bot.on("callback_query", async (ctx) => {
  const callbackData = ctx.callbackQuery.data;
  const userId = ctx.from.id.toString();

  if (callbackData === "create_wallet") {
    // Generate a deterministic wallet address
    const walletAddress = generateWalletAddress(userId);

    // Store in session
    ctx.session.walletAddress = walletAddress;

    // Store wallet info
    storeWalletInfo(userId, walletAddress);

    await ctx.reply(
      "🎉 I've created a new wallet for you!\n\n" +
        `Address: ${walletAddress}\n\n` +
        "This is a simulation for the MVP. In the full version, this would create a real smart contract wallet."
    );
  } else if (callbackData === "connect_existing") {
    await ctx.reply(
      "To connect an existing wallet, you would scan a QR code or enter your wallet address.\n\n" +
        "This feature will be implemented in the next version."
    );
  } else if (callbackData === "approve_swap") {
    if (!ctx.session.pendingSwap) {
      return ctx.reply(
        "No pending swap found. Please create a new swap request."
      );
    }

    const swap = ctx.session.pendingSwap;

    // Generate a fake transaction hash
    const txHash = `0x${Math.random().toString(16).substring(2, 62)}`;

    await ctx.reply(
      "✅ Swap approved!\n\n" +
        `Swapping ${swap.amount} ${swap.fromToken} for ~${swap.estimatedOutput} ${swap.toToken}\n\n` +
        `Transaction hash: ${txHash}\n\n` +
        "This is a simulation for the MVP. In the full version, this would execute the actual swap transaction."
    );

    // Clear the pending swap
    ctx.session.pendingSwap = null;
  } else if (callbackData === "cancel_swap") {
    ctx.session.pendingSwap = null;
    await ctx.reply("Swap cancelled.");
  }

  // Answer the callback query to remove the loading state
  await ctx.answerCallbackQuery();
});

// Handle regular messages
bot.on("message", async (ctx) => {
  const message = ctx.message.text;

  if (!message) return;

  console.log(`Received message from user ${ctx.from.id}: ${message}`);

  try {
    // Forward to our dedicated Telegram endpoint
    const requestBody = createTelegramRequestBody(ctx.from.id, message);
    console.log(`Sending to API: ${API_URL}/api/messaging/telegram/process`);
    console.log(`Request body: ${JSON.stringify(requestBody)}`);

    const response = await fetch(`${API_URL}/api/messaging/telegram/process`, {
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
    console.log(`API response: ${JSON.stringify(data)}`);

    // Send the response back to the user
    await ctx.reply(data.content);
  } catch (error) {
    console.error(`Error processing message: ${error.message}`);
    console.error(error.stack);

    // Send a friendly error message
    await ctx.reply(
      "Sorry, I encountered an error processing your request. Please try again later."
    );
  }
});

// Export Express app for Vercel serverless deployment
import express from "express";
const app = express();

// Health check endpoint for Vercel
app.get("/", (req, res) => {
  res.send({
    status: "ok",
    message: "Telegram bot is running",
    version: "1.0.0",
    timestamp: new Date().toISOString(),
    mode: process.env.NODE_ENV === "production" ? "polling" : "development",
  });
});

// Test endpoint to check bot status
app.get("/status", async (req, res) => {
  try {
    const response = await fetch(
      `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/getMe`
    );
    const data = await response.json();

    res.send({
      status: "ok",
      bot_info: data.result,
      api_url: API_URL,
      mode: process.env.NODE_ENV === "production" ? "polling" : "development",
      environment: process.env.NODE_ENV || "development",
      started_at: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).send({
      status: "error",
      message: error.message,
    });
  }
});

// Start polling in all environments, no more webhook in production
console.log(
  `Starting bot in ${process.env.NODE_ENV || "development"} mode with polling`
);
bot.start({
  drop_pending_updates: true,
  allowed_updates: ["message", "callback_query"],
});

// Set up a keepalive mechanism for Vercel to prevent the serverless function from shutting down
// This is a workaround for Vercel's serverless functions which typically shut down after a period of inactivity
if (process.env.NODE_ENV === "production") {
  console.log("Setting up keepalive mechanism for Vercel");

  // Self-ping every 5 minutes to keep the bot alive
  const PING_INTERVAL = 5 * 60 * 1000; // 5 minutes

  setInterval(async () => {
    try {
      // Call our own status endpoint to keep the function warm
      const pingUrl = `https://${
        process.env.VERCEL_URL || "snel-telegram.vercel.app"
      }/status`;
      console.log(`Pinging self at ${pingUrl} to stay alive`);

      const response = await fetch(pingUrl);
      if (response.ok) {
        console.log(`Keepalive ping successful at ${new Date().toISOString()}`);
      } else {
        console.error(`Keepalive failed with status: ${response.status}`);
      }
    } catch (error) {
      console.error("Keepalive ping failed:", error);
    }
  }, PING_INTERVAL);
}

// Export for Vercel
export default app;

// Start the express server for local development
if (process.env.NODE_ENV !== "production") {
  const PORT = process.env.PORT || 3001;
  app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
  });
}

console.log("Bot initialized!");
