import bot from "../index.js";

// This is a Vercel serverless function that handles webhook updates from Telegram
export default async function handler(req, res) {
  // Only accept POST requests
  if (req.method !== "POST") {
    res.status(200).json({ message: "Telegram webhook endpoint is active" });
    return;
  }

  try {
    // Process the update
    await bot.handleUpdate(req.body);
    res.status(200).json({ success: true });
  } catch (error) {
    console.error("Error handling webhook:", error);
    res.status(500).json({ error: "Failed to process update" });
  }
}
