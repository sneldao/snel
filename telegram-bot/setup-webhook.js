import fetch from "node-fetch";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const WEBHOOK_URL = process.env.WEBHOOK_URL;

// Check if required environment variables are set
if (!TELEGRAM_BOT_TOKEN) {
  console.error(
    "Error: TELEGRAM_BOT_TOKEN is not set in environment variables"
  );
  process.exit(1);
}

if (!WEBHOOK_URL) {
  console.error("Error: WEBHOOK_URL is not set in environment variables");
  console.error("Example: https://your-vercel-app.vercel.app/api/webhook");
  process.exit(1);
}

/**
 * Set the webhook for the Telegram bot
 */
async function setWebhook() {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook`;

  try {
    console.log(`Setting webhook to: ${WEBHOOK_URL}`);

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: WEBHOOK_URL,
        drop_pending_updates: true,
      }),
    });

    const data = await response.json();

    if (data.ok) {
      console.log("✅ Webhook set successfully!");
      return true;
    } else {
      console.error("❌ Failed to set webhook:", data.description);
      return false;
    }
  } catch (error) {
    console.error("❌ Error setting webhook:", error.message);
    return false;
  }
}

/**
 * Get information about the current webhook
 */
async function getWebhookInfo() {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo`;

  try {
    const response = await fetch(url);
    const data = await response.json();

    if (data.ok) {
      console.log("\nCurrent webhook information:");
      console.log("URL:", data.result.url);
      console.log(
        "Has custom certificate:",
        data.result.has_custom_certificate
      );
      console.log("Pending update count:", data.result.pending_update_count);

      if (data.result.last_error_date) {
        const errorDate = new Date(data.result.last_error_date * 1000);
        console.log("Last error:", data.result.last_error_message);
        console.log("Last error date:", errorDate.toISOString());
      }

      return data.result;
    } else {
      console.error("Failed to get webhook info:", data.description);
      return null;
    }
  } catch (error) {
    console.error("Error getting webhook info:", error.message);
    return null;
  }
}

/**
 * Main function to set up the webhook
 */
async function main() {
  console.log("🤖 Telegram Bot Webhook Setup");
  console.log("============================");

  // Get current webhook info
  console.log("\nChecking current webhook...");
  await getWebhookInfo();

  // Set the webhook
  console.log("\nSetting up webhook...");
  const success = await setWebhook();

  if (success) {
    // Verify the webhook was set correctly
    console.log("\nVerifying webhook setup...");
    await getWebhookInfo();

    console.log("\n✅ Webhook setup complete!");
    console.log("Your bot should now receive updates via the webhook.");
  } else {
    console.log("\n❌ Webhook setup failed. Please check the errors above.");
    process.exit(1);
  }
}

// Run the main function
main().catch((error) => {
  console.error("Unhandled error:", error);
  process.exit(1);
});
