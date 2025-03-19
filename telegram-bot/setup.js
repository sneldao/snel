#!/usr/bin/env node
/**
 * Telegram Integration Setup Script
 *
 * This script provides a one-command setup for the Telegram integration:
 * 1. Verifies the FastAPI app is running
 * 2. Tests the Telegram integration
 * 3. Sets up the webhook using ngrok
 *
 * Usage:
 * node setup.js
 */

import dotenv from "dotenv";
import axios from "axios";
import { exec, execSync } from "child_process";
import fs from "fs";
import readline from "readline";

// Load environment variables
dotenv.config();

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const API_URL = process.env.API_URL || "http://localhost:8000";
const WEBHOOK_PATH =
  process.env.TELEGRAM_WEBHOOK_PATH || "/api/messaging/telegram/webhook";

// Create readline interface for user input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

// Function to check if FastAPI is running
async function checkFastAPI() {
  console.log("🔍 Checking if FastAPI app is running...");

  // Try various health check endpoints
  const healthEndpoints = [
    `${API_URL}/health`,
    `${API_URL}/api/health`,
    `${API_URL}/api/health/check`,
  ];

  for (const endpoint of healthEndpoints) {
    try {
      console.log(`Trying endpoint: ${endpoint}`);
      const response = await axios.get(endpoint);
      if (response.status === 200) {
        console.log(`✅ FastAPI app is running! Confirmed with ${endpoint}`);
        return true;
      }
    } catch (error) {
      console.log(`Endpoint ${endpoint} failed: ${error.message}`);
      // Continue to the next endpoint
    }
  }

  // If we got here, none of the health endpoints worked
  console.error("❌ FastAPI app is not reachable!");

  const answer = await askQuestion(
    "Do you want to start the FastAPI app now? (y/n): "
  );
  if (answer.toLowerCase() === "y") {
    console.log(
      "\nTo start the FastAPI app, run the following in a new terminal:"
    );
    console.log("\x1b[33m$ cd .. && poetry run python server.py\x1b[0m");
    console.log("\nPress Enter when the FastAPI app is running...");
    await askQuestion("");

    // Try again
    return await checkFastAPI();
  }

  return false;
}

// Function to check if ngrok is running
async function checkNgrok() {
  console.log("🔍 Checking if ngrok is running...");

  try {
    const response = await axios.get("http://127.0.0.1:4040/api/tunnels");
    const tunnels = response.data.tunnels;
    const secureUrl = tunnels.find(
      (tunnel) => tunnel.proto === "https"
    )?.public_url;

    if (secureUrl) {
      console.log(`✅ ngrok is running with URL: ${secureUrl}`);
      return secureUrl;
    }
  } catch (error) {
    console.error("❌ ngrok is not running or not reachable!");

    const answer = await askQuestion("Do you want to start ngrok now? (y/n): ");
    if (answer.toLowerCase() === "y") {
      console.log("\nTo start ngrok, run the following in a new terminal:");
      console.log("\x1b[33m$ ngrok http 8000\x1b[0m");
      console.log("\nPress Enter when ngrok is running...");
      await askQuestion("");

      // Try again
      return await checkNgrok();
    }

    return null;
  }
}

// Function to verify Telegram bot token
async function verifyBotToken() {
  console.log("🔍 Verifying Telegram bot token...");

  if (!BOT_TOKEN) {
    console.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables");

    const answer = await askQuestion(
      "Do you want to enter your bot token now? (y/n): "
    );
    if (answer.toLowerCase() === "y") {
      const token = await askQuestion("Enter your Telegram bot token: ");

      // Update .env file with the token
      try {
        let envContent = "";

        if (fs.existsSync(".env")) {
          envContent = fs.readFileSync(".env", "utf8");

          // Replace token if it exists
          if (envContent.includes("TELEGRAM_BOT_TOKEN=")) {
            envContent = envContent.replace(
              /TELEGRAM_BOT_TOKEN=.*/,
              `TELEGRAM_BOT_TOKEN=${token}`
            );
          } else {
            envContent += `\nTELEGRAM_BOT_TOKEN=${token}\n`;
          }
        } else {
          envContent = `TELEGRAM_BOT_TOKEN=${token}\n`;
        }

        fs.writeFileSync(".env", envContent);
        console.log("✅ Bot token saved to .env file");

        // Reload environment variables
        process.env.TELEGRAM_BOT_TOKEN = token;
        return token;
      } catch (error) {
        console.error(`Error updating .env file: ${error.message}`);
        return null;
      }
    }

    return null;
  }

  try {
    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/getMe`
    );
    if (response.data.ok) {
      const bot = response.data.result;
      console.log(
        `✅ Bot token is valid! Bot name: ${bot.first_name} (@${bot.username})`
      );
      return BOT_TOKEN;
    } else {
      console.error("❌ Bot token is invalid!");
      return null;
    }
  } catch (error) {
    console.error(`❌ Error verifying bot token: ${error.message}`);
    return null;
  }
}

// Function to test the API integration
async function testIntegration() {
  console.log("🧪 Testing API integration...");

  try {
    // Create a test Telegram update object
    const testUpdate = {
      update_id: 123456789,
      message: {
        message_id: 123,
        from: {
          id: 12345,
          is_bot: false,
          first_name: "Test",
          last_name: "User",
          username: "testuser",
          language_code: "en",
        },
        chat: {
          id: 12345,
          first_name: "Test",
          last_name: "User",
          username: "testuser",
          type: "private",
        },
        date: Math.floor(Date.now() / 1000),
        text: "/test Integration test",
      },
    };

    const response = await axios.post(`${API_URL}${WEBHOOK_PATH}`, testUpdate, {
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 200) {
      console.log("✅ API integration test successful!");
      return true;
    } else {
      console.error(`❌ API returned status code: ${response.status}`);
      return false;
    }
  } catch (error) {
    console.error(`❌ Error testing API integration: ${error.message}`);
    if (error.response) {
      console.error(
        `Status: ${error.response.status}, Data:`,
        error.response.data
      );
    }
    return false;
  }
}

// Function to set up the webhook
async function setupWebhook(ngrokUrl) {
  console.log("🔧 Setting up Telegram webhook...");

  const webhookUrl = `${ngrokUrl}${WEBHOOK_PATH}`;

  try {
    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${webhookUrl}`
    );

    if (response.data.ok) {
      console.log(`✅ Webhook set up successfully: ${webhookUrl}`);
      return true;
    } else {
      console.error(
        `❌ Error setting up webhook: ${response.data.description}`
      );
      return false;
    }
  } catch (error) {
    console.error(`❌ Error setting up webhook: ${error.message}`);
    if (error.response) {
      console.error(
        `Status: ${error.response.status}, Data:`,
        error.response.data
      );
    }
    return false;
  }
}

// Helper function to ask questions
function askQuestion(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

// Main function
async function main() {
  console.log("🤖 Telegram Integration Setup");
  console.log("============================");

  // Step 1: Check if FastAPI is running
  const apiRunning = await checkFastAPI();
  if (!apiRunning) {
    console.error("❌ Cannot continue without FastAPI app running");
    rl.close();
    return;
  }

  // Step 2: Verify bot token
  const botToken = await verifyBotToken();
  if (!botToken) {
    console.error("❌ Cannot continue without valid bot token");
    rl.close();
    return;
  }

  // Step 3: Check if ngrok is running
  const ngrokUrl = await checkNgrok();
  if (!ngrokUrl) {
    console.error("❌ Cannot continue without ngrok URL");
    rl.close();
    return;
  }

  // Step 4: Test API integration
  const integrationOk = await testIntegration();
  if (!integrationOk) {
    console.warn("⚠️ API integration test failed, but continuing anyway...");
    const answer = await askQuestion("Do you want to continue anyway? (y/n): ");
    if (answer.toLowerCase() !== "y") {
      rl.close();
      return;
    }
  }

  // Step 5: Set up webhook
  const webhookOk = await setupWebhook(ngrokUrl);
  if (!webhookOk) {
    console.error("❌ Failed to set up webhook");
    rl.close();
    return;
  }

  console.log("\n🎉 Telegram integration set up successfully!");
  console.log("\nNext steps:");
  console.log("1. Send a message to your bot on Telegram");
  console.log("2. Try the /start command");
  console.log("3. Check your FastAPI logs for any errors");

  rl.close();
}

// Run the main function
main().catch(console.error);
