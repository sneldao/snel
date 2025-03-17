#!/usr/bin/env node
/**
 * Simple utility script to manage Telegram bot webhook
 *
 * Commands:
 * - set: Set the webhook URL
 * - info: Get webhook information
 * - delete: Delete the webhook
 *
 * Usage:
 * node webhook-manager.js set <webhook_url>
 * node webhook-manager.js info
 * node webhook-manager.js delete
 */

import dotenv from "dotenv";
import axios from "axios";

// Load environment variables
dotenv.config();

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const MAIN_APP_URL =
  process.env.API_URL || "https://snel-pointless.vercel.app/api";

if (!BOT_TOKEN) {
  console.error("Error: TELEGRAM_BOT_TOKEN not found in environment variables");
  process.exit(1);
}

const command = process.argv[2]?.toLowerCase();
const webhookUrl =
  process.argv[3] || `${MAIN_APP_URL}/messaging/telegram/webhook`;

async function setWebhook(url) {
  try {
    console.log(`Setting webhook to: ${url}`);
    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${url}`
    );
    console.log("Response:", response.data);
  } catch (error) {
    console.error("Error setting webhook:", error.message);
    if (error.response) {
      console.error("API response:", error.response.data);
    }
  }
}

async function getWebhookInfo() {
  try {
    console.log("Getting webhook information...");
    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo`
    );
    console.log("Webhook info:");
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error) {
    console.error("Error getting webhook info:", error.message);
    if (error.response) {
      console.error("API response:", error.response.data);
    }
  }
}

async function deleteWebhook() {
  try {
    console.log("Deleting webhook...");
    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook`
    );
    console.log("Response:", response.data);
  } catch (error) {
    console.error("Error deleting webhook:", error.message);
    if (error.response) {
      console.error("API response:", error.response.data);
    }
  }
}

async function getBotInfo() {
  try {
    console.log("Getting bot information...");
    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/getMe`
    );
    console.log("Bot info:");
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error) {
    console.error("Error getting bot info:", error.message);
    if (error.response) {
      console.error("API response:", error.response.data);
    }
  }
}

async function main() {
  switch (command) {
    case "set":
      await setWebhook(webhookUrl);
      break;
    case "info":
      await getWebhookInfo();
      break;
    case "delete":
      await deleteWebhook();
      break;
    case "bot":
      await getBotInfo();
      break;
    default:
      console.log(`
Telegram Bot Webhook Manager

Commands:
  set [url]   - Set the webhook URL (default: ${MAIN_APP_URL}/messaging/telegram/webhook)
  info        - Show current webhook information
  delete      - Delete current webhook
  bot         - Show bot information

Examples:
  node webhook-manager.js set
  node webhook-manager.js set https://example.com/webhook
  node webhook-manager.js info
  node webhook-manager.js delete
  node webhook-manager.js bot
      `);
  }
}

main().catch(console.error);
