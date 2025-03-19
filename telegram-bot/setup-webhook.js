#!/usr/bin/env node
/**
 * Set up Telegram webhook with ngrok
 *
 * This script automatically detects your ngrok URL and configures
 * the Telegram webhook to point to it.
 *
 * Usage:
 * node setup-webhook.js
 */

import dotenv from "dotenv";
import axios from "axios";
import { execSync } from "child_process";
import fs from "fs";
import readline from "readline";

// Load environment variables
dotenv.config();

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const WEBHOOK_PATH =
  process.env.TELEGRAM_WEBHOOK_PATH || "/api/messaging/telegram/webhook";

if (!BOT_TOKEN) {
  console.error("Error: TELEGRAM_BOT_TOKEN not found in environment variables");
  process.exit(1);
}

/**
 * Get the current ngrok URL from the ngrok client
 */
async function getNgrokUrl() {
  try {
    // Try to get the URL from the ngrok API first
    try {
      const response = await axios.get("http://127.0.0.1:4040/api/tunnels");
      const tunnels = response.data.tunnels;
      const secureUrl = tunnels.find(
        (tunnel) => tunnel.proto === "https"
      )?.public_url;

      if (secureUrl) {
        console.log(`Found ngrok URL via API: ${secureUrl}`);
        return secureUrl;
      }
    } catch (e) {
      console.log("Could not get ngrok URL via API, trying alternative method");
    }

    // Alternative: Check if ngrok is running using command line
    const output = execSync("ps aux | grep ngrok").toString();
    const match = output.match(/https:\/\/[a-zA-Z0-9-]+\.ngrok-free\.app/);

    if (match) {
      const url = match[0];
      console.log(`Found ngrok URL via command line: ${url}`);
      return url;
    }

    // If all else fails, ask the user
    console.log("Could not automatically detect ngrok URL.");
    console.log(
      "Please enter your ngrok URL manually (e.g., https://your-url.ngrok-free.app):"
    );

    // Wait for user input
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    return new Promise((resolve) => {
      rl.question("> ", (url) => {
        rl.close();
        resolve(url.trim());
      });
    });
  } catch (error) {
    console.error("Error detecting ngrok URL:", error.message);
    return null;
  }
}

/**
 * Set the webhook URL for the Telegram bot
 */
async function setWebhook(url) {
  try {
    const fullUrl = `${url}${WEBHOOK_PATH}`;
    console.log(`Setting webhook to: ${fullUrl}`);

    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${fullUrl}`
    );

    console.log("Response:", response.data);

    if (response.data.ok) {
      console.log("\n✅ Webhook set successfully!");

      // Save the webhook URL to a file for future reference
      const webhookInfo = {
        url: fullUrl,
        timestamp: new Date().toISOString(),
        success: true,
      };

      fs.writeFileSync(
        "webhook-info.json",
        JSON.stringify(webhookInfo, null, 2)
      );
      console.log("Webhook info saved to webhook-info.json");

      return true;
    } else {
      console.error("Failed to set webhook:", response.data.description);
      return false;
    }
  } catch (error) {
    console.error("Error setting webhook:", error.message);
    if (error.response) {
      console.error("API response:", error.response.data);
    }
    return false;
  }
}

/**
 * Get webhook information
 */
async function getWebhookInfo() {
  try {
    console.log("Getting current webhook information...");
    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo`
    );
    console.log("Current webhook info:");
    console.log(JSON.stringify(response.data, null, 2));
    return response.data.result;
  } catch (error) {
    console.error("Error getting webhook info:", error.message);
    if (error.response) {
      console.error("API response:", error.response.data);
    }
    return null;
  }
}

/**
 * Main function
 */
async function main() {
  console.log("🤖 Telegram Webhook Setup");
  console.log("-------------------------");

  // Check if the server is running
  try {
    console.log("Checking if server is running...");
    const healthEndpoints = [
      `${API_URL}/health`,
      `${API_URL}/api/health`,
      `${API_URL}/api/health/check`,
    ];

    let serverRunning = false;
    for (const endpoint of healthEndpoints) {
      try {
        const response = await axios.get(endpoint, { timeout: 5000 });
        if (response.status === 200) {
          console.log(`✅ Server is running! Confirmed with ${endpoint}`);
          serverRunning = true;
          break;
        }
      } catch (error) {
        // Continue trying other endpoints
      }
    }

    if (!serverRunning) {
      console.warn("⚠️ Could not confirm server is running via health check");
      console.log(
        "Make sure the server is running with: poetry run python server.py"
      );

      const shouldContinue = await new Promise((resolve) => {
        const rl = readline.createInterface({
          input: process.stdin,
          output: process.stdout,
        });
        rl.question("Continue anyway? (y/n) ", (answer) => {
          rl.close();
          resolve(answer.toLowerCase() === "y");
        });
      });

      if (!shouldContinue) {
        console.log("Operation cancelled.");
        return;
      }
    }
  } catch (error) {
    console.warn(`⚠️ Error checking server status: ${error.message}`);
  }

  // First, get information about the current webhook
  const webhookInfo = await getWebhookInfo();

  if (webhookInfo && webhookInfo.url) {
    console.log(`\nCurrent webhook is set to: ${webhookInfo.url}`);

    if (webhookInfo.pending_update_count > 0) {
      console.log(
        `There are ${webhookInfo.pending_update_count} pending updates`
      );
    }

    // Ask if user wants to change the webhook
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    const shouldContinue = await new Promise((resolve) => {
      rl.question("Do you want to update the webhook URL? (y/n) ", (answer) => {
        rl.close();
        resolve(answer.toLowerCase() === "y");
      });
    });

    if (!shouldContinue) {
      console.log("Operation cancelled. Webhook remains unchanged.");
      return;
    }
  }

  // Get the ngrok URL
  const ngrokUrl = await getNgrokUrl();

  if (!ngrokUrl) {
    console.error("Could not determine ngrok URL. Exiting.");
    process.exit(1);
  }

  // Set the webhook
  const success = await setWebhook(ngrokUrl);

  if (success) {
    console.log("\n⚙️ Next steps:");
    console.log(
      "1. Make sure your FastAPI app is running with: poetry run python server.py"
    );
    console.log("2. Test the webhook by sending a message to your bot");
    console.log(`3. Check the logs to see if the messages are being processed`);

    // Save the ngrok URL to .env file for future use
    try {
      let envContent = "";

      if (fs.existsSync(".env")) {
        envContent = fs.readFileSync(".env", "utf8");

        // Replace API_URL if it exists
        if (envContent.includes("API_URL=")) {
          envContent = envContent.replace(/API_URL=.*/, `API_URL=${ngrokUrl}`);
        } else {
          envContent += `\nAPI_URL=${ngrokUrl}\n`;
        }
      } else {
        envContent = `API_URL=${ngrokUrl}\n`;
      }

      fs.writeFileSync(".env", envContent);
      console.log(`✅ Updated API_URL in .env file to: ${ngrokUrl}`);
    } catch (error) {
      console.error(`Error updating .env file: ${error.message}`);
    }
  } else {
    console.log(
      "\n⚠️ Failed to set webhook. Please check the error messages above."
    );
  }
}

main().catch(console.error);
