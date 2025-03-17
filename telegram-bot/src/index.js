import "dotenv/config";
import { Telegraf, Markup } from "telegraf";
import axios from "axios";
import express from "express";
import {
  generateWalletAddress,
  storeWalletInfo,
  getWalletInfo,
  getWalletBalance,
} from "./wallet.js";

// Set API URL with fallback for production
const API_URL = process.env.API_URL || "https://snel-pointless.vercel.app/api";

// Initialize Express app
const app = express();

// Configure middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Initialize the bot
const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN);

// Store sessions in memory (simple approach for serverless)
const sessions = new Map();

// Session middleware
bot.use((ctx, next) => {
  const userId = ctx.from?.id.toString();
  if (!userId) return next();

  if (!sessions.has(userId)) {
    sessions.set(userId, {
      walletAddress: null,
      pendingSwap: null,
    });
  }

  ctx.session = sessions.get(userId);
  return next();
});

// Log startup information
console.log(`Starting bot with API_URL: ${API_URL}`);
console.log(
  `Running in ${process.env.NODE_ENV || "development"} mode with polling`
);
console.log(
  `Telegram Bot Token (first 5 chars): ${
    process.env.TELEGRAM_BOT_TOKEN?.substring(0, 5) || "not set"
  }`
);

// Command handlers
bot.start(async (ctx) => {
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

bot.help(async (ctx) => {
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
  const keyboard = Markup.inlineKeyboard([
    [
      Markup.button.callback("Create New Wallet", "create_wallet"),
      Markup.button.callback("Connect Existing", "connect_existing"),
    ],
  ]);

  await ctx.reply(
    "Let's set up your wallet. You can create a new wallet or connect an existing one:",
    keyboard
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

  try {
    // Use the dedicated Telegram endpoint
    console.log(`Sending price request to API for ${token}`);
    const response = await axios.post(
      `${API_URL}/api/messaging/telegram/process`,
      createTelegramRequestBody(ctx.from.id, `price of ${token}`),
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    console.log(`Received response from API: ${JSON.stringify(response.data)}`);
    await ctx.reply(response.data.content);
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

  const keyboard = Markup.inlineKeyboard([
    [
      Markup.button.callback("Approve Swap", "approve_swap"),
      Markup.button.callback("Cancel", "cancel_swap"),
    ],
  ]);

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
    keyboard
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

  // Answer the callback query
  await ctx.answerCbQuery();
});

// Handle regular messages
bot.on("message", async (ctx) => {
  // Skip non-text messages
  if (!ctx.message.text) return;

  const message = ctx.message.text;
  const userId = ctx.from.id.toString();

  console.log(`Received message from user ${userId}: ${message}`);

  try {
    // Forward to our dedicated Telegram endpoint
    const requestBody = createTelegramRequestBody(userId, message);
    console.log(`Sending to API: ${API_URL}/api/messaging/telegram/process`);
    console.log(`Request body: ${JSON.stringify(requestBody)}`);

    const response = await axios.post(
      `${API_URL}/api/messaging/telegram/process`,
      requestBody,
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    console.log(`API response: ${JSON.stringify(response.data)}`);

    // Send the response back to the user
    await ctx.reply(response.data.content);
  } catch (error) {
    console.error(`Error processing message: ${error.message}`);
    console.error(error.stack);

    // Send a friendly error message
    await ctx.reply(
      "Sorry, I encountered an error processing your request. Please try again later."
    );
  }
});

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

// Test endpoint to manually send a message
app.get("/test-send/:chatId", async (req, res) => {
  try {
    const chatId = req.params.chatId;
    console.log(`Manual test: Attempting to send message to chat ID ${chatId}`);

    const result = await bot.telegram.sendMessage(
      chatId,
      `Test message from bot at ${new Date().toISOString()}`
    );

    console.log(`Message sent successfully: ${JSON.stringify(result)}`);

    res.send({
      status: "success",
      message: "Test message sent successfully",
      details: result,
    });
  } catch (error) {
    console.error(`Error sending test message: ${error}`);
    console.error(error.stack);

    res.status(500).send({
      status: "error",
      message: `Failed to send message: ${error.message}`,
      error: error.toString(),
    });
  }
});

// Status endpoint to check bot info
app.get("/status", async (req, res) => {
  try {
    const response = await axios.get(
      `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/getMe`
    );

    res.send({
      status: "ok",
      bot_info: response.data.result,
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

// Debug endpoint to check updates
app.get("/debug-updates", async (req, res) => {
  try {
    // Get update count from Telegram
    const response = await axios.get(
      `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/getUpdates?limit=10&offset=-10`
    );

    // Check if bot is receiving messages
    const updates = response.data.result || [];
    const updateCount = updates.length;

    // Get webhook info
    const webhookResponse = await axios.get(
      `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/getWebhookInfo`
    );

    res.send({
      status: "ok",
      updates_count: updateCount,
      recent_updates: updates,
      webhook_info: webhookResponse.data.result,
      bot_token_preview: process.env.TELEGRAM_BOT_TOKEN
        ? `${process.env.TELEGRAM_BOT_TOKEN.substring(0, 5)}...`
        : "Not set",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error(`Error checking updates: ${error}`);
    res.status(500).send({
      status: "error",
      message: error.message,
      error: error.toString(),
    });
  }
});

// Webhook handler for Telegram updates
app.post("/api/webhook", (req, res) => {
  try {
    console.log(
      "Received webhook from Telegram:",
      JSON.stringify(req.body).substring(0, 200)
    );

    // Always respond with success for now (for debugging)
    res.status(200).json({ ok: true });
  } catch (error) {
    console.error("Error handling webhook:", error);
    console.error(error.stack);
    res.sendStatus(500);
  }
});

// Set up a keepalive mechanism for Vercel
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

      const response = await axios.get(pingUrl);
      if (response.status === 200) {
        console.log(`Keepalive ping successful at ${new Date().toISOString()}`);
      } else {
        console.error(`Keepalive failed with status: ${response.status}`);
      }
    } catch (error) {
      console.error("Keepalive ping failed:", error);
    }
  }, PING_INTERVAL);
}

// Start the bot with explicit error handling and debugging
console.log("Attempting to launch bot...");
try {
  // First delete any existing webhooks
  console.log("Deleting any existing webhooks...");
  bot.telegram
    .deleteWebhook({ drop_pending_updates: true })
    .then(() => {
      console.log("Successfully deleted webhook, proceeding with launch...");

      // In production, set up webhook
      if (process.env.NODE_ENV === "production") {
        // Get the Vercel URL or use the provided domain
        const webhookDomain =
          process.env.VERCEL_URL ||
          "snel-telegram-nlme0kapm-papas-projects-5b188431.vercel.app";
        const webhookUrl = `https://${webhookDomain}/api/webhook`;

        console.log(`Setting webhook to: ${webhookUrl}`);

        // Register the webhook
        bot.telegram
          .setWebhook(webhookUrl)
          .then(() => {
            console.log("Webhook set successfully!");
          })
          .catch((error) => {
            console.error("Error setting webhook:", error);
            console.error(error.stack);
          });
      } else {
        // In development, use long polling
        console.log("Development mode: using long polling");
        bot
          .launch({
            allowedUpdates: ["message", "callback_query"],
            dropPendingUpdates: true,
          })
          .then(() => {
            console.log("Bot successfully launched with polling!");
          })
          .catch((error) => {
            console.error("Error launching bot with polling:", error);
            console.error(error.stack);
          });
      }

      // Fetch and log bot info to verify connection
      bot.telegram
        .getMe()
        .then((botInfo) => {
          console.log(`Connected as bot: ${botInfo.username} (${botInfo.id})`);
        })
        .catch((error) => {
          console.error("Error getting bot info:", error);
        });
    })
    .catch((error) => {
      console.error("Error deleting webhook:", error);
      console.error(error.stack);
    });
} catch (error) {
  console.error("Exception during bot launch:", error);
  console.error(error.stack);
}

// Enable graceful stop
process.once("SIGINT", () => {
  console.log("SIGINT received, stopping bot...");
  bot.stop("SIGINT");
});
process.once("SIGTERM", () => {
  console.log("SIGTERM received, stopping bot...");
  bot.stop("SIGTERM");
});

// Express server
const PORT = process.env.PORT || 3002;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

// Export for Vercel
export default app;
