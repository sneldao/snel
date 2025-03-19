#!/usr/bin/env node
/**
 * Verify FastAPI Telegram Integration
 *
 * This script tests whether the FastAPI Telegram integration
 * is working correctly by sending a test webhook event to your API.
 *
 * Usage:
 * node verify-integration.js [api_url]
 */

import dotenv from "dotenv";
import axios from "axios";

// Load environment variables
dotenv.config();

// Default API URL if not provided as argument
const API_URL =
  process.argv[2] || process.env.API_URL || "http://localhost:8000";
const WEBHOOK_PATH =
  process.env.TELEGRAM_WEBHOOK_PATH || "/api/messaging/telegram/webhook";

// Create a test Telegram update object
const testUpdate = {
  update_id: 123456789,
  message: {
    message_id: 123,
    from: {
      id: 12345, // This is the Telegram user ID
      is_bot: false,
      first_name: "Test",
      last_name: "User",
      username: "testuser",
      language_code: "en",
    },
    chat: {
      id: 12345, // This is the chat ID (same as user ID for private chats)
      first_name: "Test",
      last_name: "User",
      username: "testuser",
      type: "private",
    },
    date: Math.floor(Date.now() / 1000),
    text: "/test Integration test from verify-integration.js",
  },
};

// Function to test the webhook endpoint
async function testWebhook() {
  console.log("🧪 Testing Telegram Integration");
  console.log("-------------------------------");
  console.log(`API URL: ${API_URL}`);
  console.log(`Webhook Path: ${WEBHOOK_PATH}`);
  console.log(`Full URL: ${API_URL}${WEBHOOK_PATH}`);
  console.log("\nSending test webhook event...");

  try {
    console.log(`POSTing to ${API_URL}${WEBHOOK_PATH}...`);
    const response = await axios.post(`${API_URL}${WEBHOOK_PATH}`, testUpdate, {
      headers: {
        "Content-Type": "application/json",
      },
      timeout: 10000, // 10 second timeout
    });

    console.log("\n✅ Request sent successfully!");
    console.log("Status:", response.status);
    console.log("Response:", response.data);

    console.log(
      "\nIf you see a 200 status code and a response with 'status: processing',"
    );
    console.log("it means the FastAPI webhook endpoint is working correctly.");
    console.log(
      "\nCheck your FastAPI logs to see if the message was processed correctly."
    );
    console.log("Look for lines containing 'Processing Telegram webhook'");
    return true;
  } catch (error) {
    console.error("\n❌ Error testing webhook:");
    console.error(`Status code: ${error.response?.status || "Unknown"}`);

    if (error.response) {
      console.error("Response data:", error.response.data);
    } else if (error.code === "ECONNREFUSED") {
      console.error(
        "Connection refused. The server is not running or not accessible."
      );
    } else if (error.code === "ETIMEDOUT" || error.code === "ECONNABORTED") {
      console.error("Request timed out. The server might be slow to respond.");
    } else {
      console.error("Error details:", error.message);
    }

    console.log("\n🔍 Troubleshooting tips:");
    console.log(
      "1. Make sure your FastAPI app is running with 'poetry run python server.py'"
    );
    console.log("2. Check that the API URL is correct");
    console.log("3. Verify that the webhook path is correct");
    console.log("4. Look at your FastAPI logs for errors");
    console.log(
      "5. Try running 'curl -X POST " +
        API_URL +
        WEBHOOK_PATH +
        ' -H "Content-Type: application/json" -d "{}"\' to test the endpoint directly'
    );

    return false;
  }
}

// Function to test the messaging router process endpoint
async function testProcessEndpoint() {
  console.log("\n🧪 Testing Direct Message Processing");
  console.log("-----------------------------------");

  // Try multiple possible endpoint variations
  const possibleProcessUrls = [
    `${API_URL}/api/messaging/telegram/process`,
    `${API_URL}/api/telegram/process`,
    `${API_URL}/api/webhook/telegram/process`,
  ];

  console.log(`Trying multiple possible endpoints:`);
  possibleProcessUrls.forEach((url) => console.log(`- ${url}`));

  const testMessage = {
    platform: "telegram",
    user_id: "12345",
    message: "/test Integration test message",
  };

  let success = false;

  for (const processUrl of possibleProcessUrls) {
    try {
      console.log(`\nTrying endpoint: ${processUrl}`);
      console.log("Sending test message...");
      const response = await axios.post(processUrl, testMessage, {
        headers: {
          "Content-Type": "application/json",
        },
        timeout: 10000, // 10 second timeout
      });

      console.log("\n✅ Request sent successfully!");
      console.log("Status:", response.status);
      console.log("Response:", response.data);

      console.log(
        "\nIf you see a 200 status code and a content field in the response,"
      );
      console.log(
        "it means the message processing endpoint is working correctly."
      );

      success = true;
      break; // Break out of the loop if successful
    } catch (error) {
      console.error(`\n❌ Error testing process endpoint at ${processUrl}:`);
      console.error(`Status code: ${error.response?.status || "Unknown"}`);

      if (error.response) {
        console.error("Response data:", error.response.data);
      } else if (error.code === "ECONNREFUSED") {
        console.error(
          "Connection refused. The server is not running or not accessible."
        );
      } else if (error.code === "ETIMEDOUT" || error.code === "ECONNABORTED") {
        console.error(
          "Request timed out. The server might be slow to respond."
        );
      } else {
        console.error("Error details:", error.message);
      }

      // Continue to try the next URL if this one failed
    }
  }

  if (!success) {
    console.error("\n❌ All process endpoint URLs failed.");
    console.log("\n🔍 Troubleshooting tips:");
    console.log(
      "1. Make sure your FastAPI app is running with 'poetry run python server.py'"
    );
    console.log("2. Check your FastAPI logs for errors");
    console.log("3. Verify the API is configured to handle Telegram messages");
    console.log("4. The process endpoint may have a different URL structure");
  }

  return success;
}

// Main function
async function main() {
  try {
    console.log("🔍 Checking server status...");

    // Try a simple health check first
    try {
      const healthEndpoints = [
        `${API_URL}/health`,
        `${API_URL}/api/health`,
        `${API_URL}/api/health/check`,
      ];

      let serverRunning = false;

      for (const endpoint of healthEndpoints) {
        try {
          console.log(`Trying health endpoint: ${endpoint}`);
          const response = await axios.get(endpoint, { timeout: 5000 });
          if (response.status === 200) {
            console.log(`✅ Server is running! Confirmed with ${endpoint}`);
            serverRunning = true;
            break;
          }
        } catch (error) {
          console.log(`Health endpoint ${endpoint} failed: ${error.message}`);
        }
      }

      if (!serverRunning) {
        console.warn(
          "⚠️ Could not confirm server is running through health checks"
        );
        console.log(
          "Make sure the server is running with: poetry run python server.py"
        );
        console.log("Continuing with integration tests anyway...");
      }
    } catch (error) {
      console.warn(
        "⚠️ Health check failed, but continuing with integration tests"
      );
    }

    // Test the webhook endpoint
    console.log("\n-----------------------------------------");
    const webhookResult = await testWebhook();

    // Test the process endpoint
    console.log("\n-----------------------------------------");
    const processResult = await testProcessEndpoint();

    console.log("\n-----------------------------------------");
    console.log("🔄 Integration Test Results:");

    if (webhookResult && processResult) {
      console.log(
        "✅ Both tests passed! Your API is set up correctly for Telegram integration."
      );
    } else if (webhookResult) {
      console.log("⚠️ Webhook test passed but process endpoint test failed.");
      console.log(
        "This is okay for basic functionality, but some features may not work correctly."
      );
    } else if (processResult) {
      console.log("⚠️ Process endpoint test passed but webhook test failed.");
      console.log("Your webhook configuration may need adjustment.");
    } else {
      console.log(
        "❌ Both tests failed. Your API may not be properly configured for Telegram."
      );
    }

    console.log("\n🔄 Next steps:");

    if (webhookResult || processResult) {
      console.log("1. Set up the webhook URL using setup-webhook.js");
      console.log(
        "2. Test with your actual Telegram bot by sending a message to it"
      );
      console.log("3. Check the server logs for any errors");

      return 0; // Success exit code
    } else {
      console.log(
        "1. Verify your FastAPI server is running: poetry run python server.py"
      );
      console.log("2. Check the server logs for any errors");
      console.log(
        "3. Make sure the Telegram routes are properly configured in your FastAPI app"
      );
      console.log("4. Try running the tests again after fixing any issues");

      return 1; // Error exit code
    }
  } catch (error) {
    console.error("\nAn unexpected error occurred:", error.message);
    return 1; // Error exit code
  }
}

// Run the main function and handle exit code
main()
  .then((exitCode) => {
    if (exitCode !== 0) {
      process.exit(exitCode);
    }
  })
  .catch((error) => {
    console.error("Unhandled error:", error);
    process.exit(1);
  });
