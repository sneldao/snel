import axios from "axios";
import "dotenv/config";

// URL to test
const API_URL = process.env.API_URL || "https://snel-pointless.vercel.app/api";
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

// Log the API URL being used
console.log(`Using API_URL from environment: ${process.env.API_URL}`);

// Test the API connection
async function testApiConnection() {
  try {
    console.log(`Testing connection to API: ${API_URL}`);
    const response = await axios.post(
      `${API_URL}/api/messaging/telegram/process`,
      {
        platform: "telegram",
        user_id: "123456",
        message: "hello",
        metadata: {
          source: "telegram_bot",
          version: "1.0.0",
          timestamp: Date.now(),
        },
      },
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    console.log("API Connection successful!");
    console.log("Response:", response.data);
    return true;
  } catch (error) {
    console.error("API Connection failed!");
    console.error("Error:", error.message);
    return false;
  }
}

// Test Telegram Bot API
async function testTelegramBotApi() {
  try {
    console.log(
      `Testing connection to Telegram Bot API with token: ${BOT_TOKEN.substring(
        0,
        5
      )}...`
    );
    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/getMe`
    );

    console.log("Telegram Bot API connection successful!");
    console.log("Bot info:", response.data.result);
    return true;
  } catch (error) {
    console.error("Telegram Bot API connection failed!");
    console.error("Error:", error.message);
    return false;
  }
}

// Run tests
async function runTests() {
  console.log("=== Running Bot API Tests ===");

  const apiSuccess = await testApiConnection();
  const telegramSuccess = await testTelegramBotApi();

  console.log("\n=== Test Results ===");
  console.log(`API Connection: ${apiSuccess ? "SUCCESS" : "FAILED"}`);
  console.log(`Telegram Bot API: ${telegramSuccess ? "SUCCESS" : "FAILED"}`);

  if (apiSuccess && telegramSuccess) {
    console.log("\n✅ All tests passed! Your bot should work correctly.");
    console.log(
      "If it's not responding, the issue is likely with the serverless environment."
    );
  } else {
    console.log(
      "\n❌ Some tests failed. Please fix the issues above before deploying."
    );
  }
}

runTests();
