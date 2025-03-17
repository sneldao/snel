import dotenv from "dotenv";
import fetch from "node-fetch";

// Load environment variables
dotenv.config();

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const VERCEL_URL = process.env.VERCEL_URL || "";

if (!TELEGRAM_BOT_TOKEN) {
  console.error("TELEGRAM_BOT_TOKEN is not set");
  process.exit(1);
}

if (!VERCEL_URL) {
  console.error("VERCEL_URL is not set");
  process.exit(1);
}

const webhookUrl = `https://${VERCEL_URL}/api/webhook`;
console.log(`Setting webhook to: ${webhookUrl}`);

// Set the webhook
async function setWebhook() {
  try {
    const response = await fetch(
      `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: webhookUrl,
          allowed_updates: ["message", "callback_query"],
        }),
      }
    );

    const data = await response.json();

    if (data.ok) {
      console.log("Webhook set successfully!");
      console.log(data);
    } else {
      console.error("Failed to set webhook:", data);
    }
  } catch (error) {
    console.error("Error setting webhook:", error);
  }
}

// Get current webhook info
async function getWebhookInfo() {
  try {
    const response = await fetch(
      `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo`
    );

    const data = await response.json();
    console.log("Current webhook info:");
    console.log(JSON.stringify(data, null, 2));
  } catch (error) {
    console.error("Error getting webhook info:", error);
  }
}

// Run the functions
async function main() {
  await getWebhookInfo();
  await setWebhook();
  await getWebhookInfo();
}

main();
