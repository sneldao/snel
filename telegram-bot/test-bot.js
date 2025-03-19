#!/usr/bin/env node
/**
 * Script to test Telegram bot connectivity and send a test message
 *
 * Usage:
 * node test-bot.js
 */

import dotenv from "dotenv";
import axios from "axios";

// Load environment variables
dotenv.config();

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

if (!BOT_TOKEN) {
  console.error("Error: TELEGRAM_BOT_TOKEN not found in environment variables");
  process.exit(1);
}

// Function to get bot information
async function getBotInfo() {
  try {
    console.log("Getting bot information...");
    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/getMe`
    );
    console.log("Bot info:");
    console.log(JSON.stringify(response.data, null, 2));
    return response.data.result;
  } catch (error) {
    console.error("Error getting bot info:", error.message);
    if (error.response) {
      console.error("API response:", error.response.data);
    }
    return null;
  }
}

// Send a test message to Telegram
async function sendTestMessage(chatId) {
  if (!chatId) {
    console.error("Error: No chat ID provided for test message");
    console.log("Usage: node test-bot.js <chat_id>");
    console.log(
      "You can find your chat ID by messaging @userinfobot on Telegram"
    );
    return;
  }

  try {
    console.log(`Sending test message to chat ID: ${chatId}...`);
    const testMessage =
      "🤖 Hello! This is a test message from the SNEL bot. " +
      "If you received this, the bot is working correctly! " +
      "Current time: " +
      new Date().toISOString();

    const response = await axios.post(
      `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`,
      {
        chat_id: chatId,
        text: testMessage,
        parse_mode: "Markdown",
      }
    );

    console.log("Message sent successfully!");
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error) {
    console.error("Error sending test message:", error.message);
    if (error.response) {
      console.error("API response:", error.response.data);
    }
  }
}

async function main() {
  // Get bot info first
  const botInfo = await getBotInfo();

  if (!botInfo) {
    console.error(
      "Could not retrieve bot information. Please check your token."
    );
    process.exit(1);
  }

  console.log(`\nBot is active: @${botInfo.username}`);

  // Check for chat ID argument
  const chatId = process.argv[2];
  if (chatId) {
    await sendTestMessage(chatId);
  } else {
    console.log("\nTo send a test message, run the script with your chat ID:");
    console.log("node test-bot.js <your_chat_id>");
    console.log(
      "You can find your chat ID by messaging @userinfobot on Telegram"
    );
  }
}

main().catch(console.error);
