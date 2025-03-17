import { Telegraf, session } from "telegraf";
import dotenv from "dotenv";
import fetch from "node-fetch";
import * as wallet from "./wallet.js";

// Load environment variables
dotenv.config();

// Initialize the bot
const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN);
const API_URL = process.env.API_URL || "http://localhost:8000";

// Use session middleware
bot.use(
  session({
    initial: () => ({
      walletConnected: false,
      pendingAction: null,
    }),
  })
);

// Command handlers
bot.start((ctx) => {
  ctx.reply(
    "👋 Welcome to Dowse - your Scroll-native multichain DeFi assistant!\n\n" +
      "I can help you with:\n" +
      "• Checking token prices across chains\n" +
      "• Swapping tokens with the best rates\n" +
      "• Managing your crypto wallet\n" +
      "• Tracking your token balances\n\n" +
      "Try me out or visit our web app: https://snel-pointless.vercel.app/"
  );

  // Send a follow-up message with a quick tip
  setTimeout(() => {
    ctx.reply(
      "💡 Quick tip: You can check token prices by typing something like 'What's the price of ETH?' or using the /price command!"
    );
  }, 1000);
});

bot.command("help", async (ctx) => {
  await ctx.reply(
    "🔍 Available Commands:\n\n" +
      "Wallet Management:\n" +
      "• /connect - Create or connect a wallet\n" +
      "• /disconnect - Disconnect your wallet\n" +
      "• /balance - Check your wallet balance\n\n" +
      "DeFi Operations:\n" +
      "• /price [token] - Check token price\n" +
      "• /swap [amount] [token] for [token] - Swap tokens\n\n" +
      "You can also ask me questions in natural language like:\n" +
      "• 'How much is ETH worth?'\n" +
      "• 'What's the price of USDC?'\n" +
      "• 'Show me my balance'\n\n" +
      "For more information, visit: https://snel-pointless.vercel.app/"
  );
});

bot.command("connect", async (ctx) => {
  try {
    const userId = ctx.from.id.toString();

    // Check if user already has a wallet
    const hasExistingWallet = await wallet.hasWallet(userId);

    if (hasExistingWallet) {
      const walletData = await wallet.getWallet(userId);
      ctx.session.walletConnected = true;

      await ctx.reply(
        `✅ Your wallet is already connected!\n\n` +
          `Address: ${walletData.address.slice(
            0,
            6
          )}...${walletData.address.slice(-4)}\n` +
          `Chain: Scroll Sepolia Testnet\n\n` +
          `Use /balance to check your balance or /disconnect to disconnect this wallet.`
      );
      return;
    }

    // Create a new wallet
    await ctx.reply(
      "🔐 Creating a new wallet for you on Scroll Sepolia testnet..."
    );

    const newWallet = await wallet.createWallet(userId);
    ctx.session.walletConnected = true;

    await ctx.reply(
      `✅ Wallet created successfully!\n\n` +
        `Address: ${newWallet.address.slice(0, 6)}...${newWallet.address.slice(
          -4
        )}\n` +
        `Chain: Scroll Sepolia Testnet\n\n` +
        `Your wallet has been created with test tokens for you to experiment with.\n\n` +
        `⚠️ Important: This is a testnet wallet for demonstration purposes. Do not send real assets to this address.\n\n` +
        `Use /balance to check your balance.`
    );
  } catch (error) {
    console.error("Error connecting wallet:", error);
    await ctx.reply(
      "❌ Sorry, there was an error creating your wallet. Please try again later."
    );
  }
});

bot.command("disconnect", async (ctx) => {
  try {
    const userId = ctx.from.id.toString();

    // Check if user has a wallet
    const hasExistingWallet = await wallet.hasWallet(userId);

    if (!hasExistingWallet) {
      await ctx.reply(
        "❌ You don't have a connected wallet. Use /connect to create one."
      );
      return;
    }

    // Disconnect the wallet
    await wallet.disconnectWallet(userId);
    ctx.session.walletConnected = false;

    await ctx.reply("✅ Your wallet has been disconnected successfully.");
  } catch (error) {
    console.error("Error disconnecting wallet:", error);
    await ctx.reply(
      "❌ Sorry, there was an error disconnecting your wallet. Please try again later."
    );
  }
});

bot.command("balance", async (ctx) => {
  try {
    const userId = ctx.from.id.toString();

    // Check if user has a wallet
    const hasExistingWallet = await wallet.hasWallet(userId);

    if (!hasExistingWallet) {
      await ctx.reply(
        "❌ You don't have a connected wallet. Use /connect to create one."
      );
      return;
    }

    // Get wallet data
    const walletData = await wallet.getWallet(userId);

    // Get balance
    await ctx.reply(
      `🔍 Checking balance for ${walletData.address.slice(
        0,
        6
      )}...${walletData.address.slice(-4)}...`
    );

    const balances = await wallet.getBalance(walletData.address);

    let balanceMessage = `💰 Wallet Balance on Scroll Sepolia:\n\n`;
    balanceMessage += `• ${balances.ETH} ETH\n`;

    if (balances.tokens && balances.tokens.length > 0) {
      balanceMessage += `\nTokens:\n`;

      balances.tokens.forEach((token) => {
        balanceMessage += `• ${token.balance} ${token.symbol}`;

        if (token.value_usd) {
          balanceMessage += ` (≈ $${token.value_usd.toFixed(2)})`;
        }

        balanceMessage += `\n`;
      });
    }

    balanceMessage += `\n🌐 View on block explorer: https://sepolia-blockscout.scroll.io/address/${walletData.address}`;

    await ctx.reply(balanceMessage);
  } catch (error) {
    console.error("Error checking balance:", error);
    await ctx.reply(
      "❌ Sorry, there was an error checking your balance. Please try again later."
    );
  }
});

bot.command("price", async (ctx) => {
  const message = ctx.message.text.trim();
  const parts = message.split(" ");

  if (parts.length < 2) {
    await ctx.reply("Please specify a token, e.g., /price ETH");
    return;
  }

  const token = parts[1].toUpperCase();

  try {
    // Forward to the API
    const response = await fetch(`${API_URL}/api/messaging/test`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        platform: "telegram",
        user_id: ctx.from.id.toString(),
        message: `price of ${token}`,
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    const data = await response.json();
    await ctx.reply(data.content);
  } catch (error) {
    console.error("Error getting price:", error);
    await ctx.reply(
      `Sorry, I couldn't get the price for ${token}. Please try again later.`
    );
  }
});

bot.command("swap", async (ctx) => {
  const userId = ctx.from.id.toString();

  // Check if user has a wallet
  const hasWallet = await wallet.hasWallet(userId);

  if (!hasWallet) {
    await ctx.reply(
      "❌ You need to connect a wallet first. Use /connect to create one."
    );
    return;
  }

  const message = ctx.message.text.trim();

  // Store the swap intent in the session
  ctx.session.pendingAction = {
    type: "swap",
    command: message,
  };

  // Forward to the API to parse the swap
  try {
    const response = await fetch(`${API_URL}/api/messaging/test`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        platform: "telegram",
        user_id: userId,
        message: message,
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    const data = await response.json();

    // For now, just show the parsed response
    await ctx.reply(
      `🔄 Swap Request Parsed:\n\n${data.content}\n\n` +
        `⚠️ Note: This is a testnet implementation. No actual swap will be executed yet.`
    );
  } catch (error) {
    console.error("Error processing swap:", error);
    await ctx.reply(
      "❌ Sorry, there was an error processing your swap request. Please try again later."
    );
  }
});

// Handle regular messages
bot.on("message:text", async (ctx) => {
  const message = ctx.message.text.toLowerCase();

  // Handle greetings
  if (
    message.match(/^(hi|hello|hey|gm|good morning|good day|good evening)$/i)
  ) {
    await ctx.reply(
      "👋 Hello! How can I help you today? Try /help to see what I can do."
    );
    return;
  }

  // Handle price queries
  if (
    message.match(
      /price of|how much is|what is the price of|what's the price of/i
    )
  ) {
    try {
      // Forward to the API
      const response = await fetch(`${API_URL}/api/messaging/test`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          platform: "telegram",
          user_id: ctx.from.id.toString(),
          message: message,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data = await response.json();
      await ctx.reply(data.content);
      return;
    } catch (error) {
      console.error("Error getting price:", error);
      await ctx.reply(
        "Sorry, I couldn't process your price query. Please try again later."
      );
      return;
    }
  }

  // Handle balance queries
  if (message.match(/balance|my tokens|my wallet|my funds/i)) {
    // Redirect to balance command
    await ctx.reply("Checking your balance...");
    await bot.telegram.sendMessage(ctx.chat.id, "/balance", {
      entities: [{ type: "bot_command", offset: 0, length: 8 }],
    });
    return;
  }

  // Handle questions about the bot
  if (
    message.match(
      /who are you|what are you|what can you do|what is snel|what's snel/i
    )
  ) {
    await ctx.reply(
      "I'm Snel, a Scroll-native multichain DeFi assistant! 🐌\n\n" +
        "I can help you check token prices, manage your wallet, and execute swaps on Scroll Sepolia testnet.\n\n" +
        "Use /help to see all available commands."
    );
    return;
  }

  // Handle questions about Scroll
  if (message.match(/what is scroll|what's scroll|tell me about scroll/i)) {
    await ctx.reply(
      "Scroll is a zkEVM-based zkRollup on Ethereum that enables native compatibility with Ethereum applications and tools.\n\n" +
        "It offers fast transactions, low fees, and strong security through zero-knowledge proofs, while maintaining full compatibility with existing Ethereum smart contracts and developer tools.\n\n" +
        "Learn more at https://scroll.io"
    );
    return;
  }

  // Handle questions about gas fees
  if (message.match(/gas fee|gas price|transaction fee/i)) {
    await ctx.reply(
      "Gas fees on Scroll are significantly lower than on Ethereum mainnet, typically 10-20x cheaper.\n\n" +
        "This makes it perfect for smaller transactions that would be cost-prohibitive on mainnet.\n\n" +
        "For this testnet implementation, you don't need to worry about gas fees as we're using Scroll Sepolia testnet."
    );
    return;
  }

  // Default response for unrecognized messages
  await ctx.reply(
    "I'm not sure how to respond to that. Here are some things you can try:\n\n" +
      "• Check token prices: '/price ETH' or 'How much is USDC?'\n" +
      "• Manage your wallet: '/connect', '/balance', '/disconnect'\n" +
      "• Swap tokens: '/swap 0.1 ETH for USDC'\n\n" +
      "Type /help for a full list of commands or visit our web app: https://snel-pointless.vercel.app/"
  );
});

// If running in development mode (not on Vercel), use long polling
if (process.env.NODE_ENV !== "production") {
  console.log("Starting bot in development mode (long polling)...");
  bot
    .launch()
    .then(() => {
      console.log("Bot started successfully!");
    })
    .catch((err) => {
      console.error("Failed to start bot:", err);
    });
}

// Enable graceful stop
process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));

// Export a serverless function handler for Vercel
export default async function handler(req, res) {
  try {
    // Health check for GET requests
    if (req.method === "GET") {
      return res.status(200).json({
        status: "ok",
        message: "Telegram bot is running",
        timestamp: new Date().toISOString(),
      });
    }

    return res.status(200).json({
      message:
        "This endpoint is just a health check. Webhook should be at /api/webhook",
    });
  } catch (error) {
    console.error("Error in index handler:", error);
    return res.status(500).json({ error: error.message });
  }
}
