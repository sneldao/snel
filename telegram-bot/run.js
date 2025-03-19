#!/usr/bin/env node
/**
 * Telegram Integration Runner
 *
 * This script provides a simple way to run the entire Telegram integration process:
 * 1. Check if the FastAPI server is running
 * 2. Verify the integration is working
 * 3. Set up the webhook
 *
 * Usage:
 * node run.js
 */

import { exec, spawn } from "child_process";
import readline from "readline";
import axios from "axios";
import dotenv from "dotenv";
import fs from "fs";
import path from "path";

// Load environment variables
dotenv.config();

const API_URL = process.env.API_URL || "http://localhost:8000";
let serverProcess = null;
let ngrokProcess = null;

// Create readline interface for user input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

// Helper function to ask questions
function askQuestion(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

// Function to check if server is running
async function checkServerRunning() {
  console.log("🔍 Checking if FastAPI server is running...");

  const healthEndpoints = [
    `${API_URL}/health`,
    `${API_URL}/api/health`,
    `${API_URL}/api/health/check`,
  ];

  for (const endpoint of healthEndpoints) {
    try {
      const response = await axios.get(endpoint, { timeout: 5000 });
      if (response.status === 200) {
        console.log(`✅ Server is running! Confirmed with ${endpoint}`);
        return true;
      }
    } catch (error) {
      // Continue trying other endpoints
    }
  }

  return false;
}

// Function to start the server if it's not running
async function startServerIfNeeded() {
  const serverRunning = await checkServerRunning();

  if (!serverRunning) {
    console.log("❌ Server is not running");

    const answer = await askQuestion(
      "Do you want to start the server? (y/n): "
    );
    if (answer.toLowerCase() === "y") {
      console.log("\n🚀 Starting FastAPI server...");

      try {
        // Get the root directory (one level up from telegram-bot)
        const rootDir = path.resolve(__dirname, "..");

        // Check if server.py exists
        const serverPath = path.join(rootDir, "server.py");
        if (!fs.existsSync(serverPath)) {
          console.error(`❌ Could not find server.py at ${serverPath}`);
          return false;
        }

        // Start the server in a new process
        serverProcess = spawn("poetry", ["run", "python", "server.py"], {
          cwd: rootDir,
          stdio: "inherit",
          detached: true,
        });

        console.log("🕒 Waiting for server to start...");

        // Give the server some time to start
        await new Promise((resolve) => setTimeout(resolve, 5000));

        // Check if server started successfully
        let maxAttempts = 5;
        let serverStarted = false;

        while (maxAttempts > 0 && !serverStarted) {
          serverStarted = await checkServerRunning();
          if (!serverStarted) {
            console.log(
              `Waiting for server to start... (${maxAttempts} attempts left)`
            );
            await new Promise((resolve) => setTimeout(resolve, 2000));
            maxAttempts--;
          }
        }

        if (serverStarted) {
          console.log("✅ Server started successfully!");
          return true;
        } else {
          console.error("❌ Failed to start the server");
          return false;
        }
      } catch (error) {
        console.error(`❌ Error starting server: ${error.message}`);
        return false;
      }
    } else {
      return false;
    }
  }

  return true;
}

// Function to check if ngrok is running
async function checkNgrokRunning() {
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
    console.log("❌ ngrok is not running");
    return null;
  }
}

// Function to start ngrok if it's not running
async function startNgrokIfNeeded() {
  const ngrokUrl = await checkNgrokRunning();

  if (!ngrokUrl) {
    const answer = await askQuestion("Do you want to start ngrok? (y/n): ");
    if (answer.toLowerCase() === "y") {
      console.log("\n🚀 Starting ngrok...");

      try {
        // Start ngrok in a new process
        ngrokProcess = spawn("ngrok", ["http", "8000"], {
          stdio: "ignore",
          detached: true,
        });

        console.log("🕒 Waiting for ngrok to start...");

        // Give ngrok some time to start
        await new Promise((resolve) => setTimeout(resolve, 3000));

        // Check if ngrok started successfully
        const url = await checkNgrokRunning();
        if (url) {
          console.log(`✅ ngrok started successfully with URL: ${url}`);
          return url;
        } else {
          console.error("❌ Failed to start ngrok");
          return null;
        }
      } catch (error) {
        console.error(`❌ Error starting ngrok: ${error.message}`);
        return null;
      }
    } else {
      return null;
    }
  }

  return ngrokUrl;
}

// Function to verify the Telegram integration
async function verifyIntegration() {
  console.log("\n🧪 Verifying Telegram integration...");

  return new Promise((resolve) => {
    // Run verify-integration.js
    const verifyProcess = exec(
      "node verify-integration.js",
      (error, stdout, stderr) => {
        if (error) {
          console.error(`❌ Verification failed: ${error.message}`);
          resolve(false);
          return;
        }

        console.log(stdout);

        if (stderr) {
          console.error(stderr);
        }

        // Check the output for success/failure
        const success =
          stdout.includes("✅") && !stdout.includes("❌ Both tests failed");

        if (success) {
          console.log("✅ Integration verification successful!");
        } else {
          console.error("❌ Integration verification failed");
        }

        resolve(success);
      }
    );
  });
}

// Function to set up the webhook
async function setupWebhook(ngrokUrl) {
  console.log("\n🔧 Setting up Telegram webhook...");

  // Update the API_URL in the environment for the setup script
  process.env.API_URL = ngrokUrl;

  return new Promise((resolve) => {
    // Run setup-webhook.js
    const setupProcess = exec(
      "node setup-webhook.js",
      (error, stdout, stderr) => {
        if (error) {
          console.error(`❌ Webhook setup failed: ${error.message}`);
          resolve(false);
          return;
        }

        console.log(stdout);

        if (stderr) {
          console.error(stderr);
        }

        // Check the output for success
        const success = stdout.includes("Webhook set successfully");

        if (success) {
          console.log("✅ Webhook setup successful!");
        } else {
          console.error("❌ Webhook setup failed");
        }

        resolve(success);
      }
    );
  });
}

// Main function
async function main() {
  console.log("🤖 Telegram Integration Runner");
  console.log("============================");

  try {
    // Step 1: Make sure the server is running
    const serverRunning = await startServerIfNeeded();
    if (!serverRunning) {
      console.error("❌ Cannot continue without FastAPI server running");
      return 1;
    }

    // Step 2: Make sure ngrok is running
    const ngrokUrl = await startNgrokIfNeeded();
    if (!ngrokUrl) {
      console.error("❌ Cannot continue without ngrok URL");
      return 1;
    }

    // Step 3: Verify the integration
    const integrationOk = await verifyIntegration();
    if (!integrationOk) {
      const answer = await askQuestion(
        "Integration verification failed. Continue anyway? (y/n): "
      );
      if (answer.toLowerCase() !== "y") {
        return 1;
      }
    }

    // Step 4: Set up the webhook
    const webhookOk = await setupWebhook(ngrokUrl);

    // Final output
    console.log("\n==============================================");
    if (webhookOk) {
      console.log("🎉 Telegram integration set up successfully!");
      console.log("\nNext steps:");
      console.log("1. Send a message to your bot on Telegram");
      console.log("2. Try the /start command");
      console.log("3. Check your FastAPI logs for any errors");
      return 0;
    } else {
      console.error("⚠️ Telegram integration setup encountered issues");
      console.log("\nTroubleshooting steps:");
      console.log("1. Check the error messages above");
      console.log("2. Make sure your Telegram bot token is correct");
      console.log("3. Verify your server logs for detailed error messages");
      return 1;
    }
  } catch (error) {
    console.error(`❌ Unexpected error: ${error.message}`);
    return 1;
  } finally {
    // Close the readline interface
    rl.close();
  }
}

// Run the main function and handle exit code
main()
  .then((exitCode) => {
    // Don't automatically exit - keep server and ngrok running
    console.log("\n✨ Integration setup complete!");
    console.log(
      "Keep this terminal window open to maintain the server and ngrok connections."
    );
    console.log("Press Ctrl+C when you're finished testing the Telegram bot.");
  })
  .catch((error) => {
    console.error("Unhandled error:", error);
    process.exit(1);
  });
