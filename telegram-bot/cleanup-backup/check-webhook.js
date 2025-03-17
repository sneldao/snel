import "dotenv/config";
import axios from "axios";

// Get the bot token from environment
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

if (!BOT_TOKEN) {
  console.error("Error: TELEGRAM_BOT_TOKEN is not set in environment");
  process.exit(1);
}

async function checkWebhook() {
  try {
    console.log(`Getting webhook info for bot ${BOT_TOKEN.substring(0, 5)}...`);

    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo`
    );

    const webhookInfo = response.data.result;

    console.log("\n=== Webhook Information ===");
    console.log(`URL: ${webhookInfo.url || "Not set"}`);
    console.log(
      `Has custom certificate: ${webhookInfo.has_custom_certificate}`
    );
    console.log(`Pending update count: ${webhookInfo.pending_update_count}`);
    console.log(`Max connections: ${webhookInfo.max_connections || "Default"}`);

    if (webhookInfo.last_error_date) {
      const errorDate = new Date(webhookInfo.last_error_date * 1000);
      console.log(`\n⚠️ Last error: ${webhookInfo.last_error_message}`);
      console.log(`   at ${errorDate.toISOString()}`);
    }

    if (webhookInfo.url) {
      console.log("\n✅ Webhook is set up.");

      if (webhookInfo.pending_update_count > 0) {
        console.log(
          `⚠️ There are ${webhookInfo.pending_update_count} pending updates.`
        );
      }
    } else {
      console.log("\n❌ No webhook is currently set.");
    }

    console.log("\n=== Test Webhook Setup ===");

    // Get your deployment URL
    const deployUrl = process.env.VERCEL_URL || "your-app.vercel.app";

    console.log(`To set up a webhook for your bot, use:`);
    console.log(
      `https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=https://${deployUrl}/api/webhook`
    );

    console.log("\nTo delete the webhook, use:");
    console.log(`https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook`);
  } catch (error) {
    console.error("Error checking webhook:", error.message);
    console.error(error.stack);
  }
}

checkWebhook();
