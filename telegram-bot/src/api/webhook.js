import { bot } from "../index.js";

// This is a Vercel serverless function that handles webhook updates from Telegram
export default async function handler(req, res) {
  try {
    // Health check for GET requests
    if (req.method === "GET") {
      return res.status(200).json({
        status: "ok",
        message: "Telegram webhook endpoint is active",
        timestamp: new Date().toISOString(),
      });
    }

    // Only accept POST requests
    if (req.method !== "POST") {
      return res.status(405).json({
        error: "Method not allowed",
        allowed: ["GET", "POST"],
      });
    }

    // Validate the request body
    if (!req.body || typeof req.body !== "object") {
      return res.status(400).json({
        error: "Invalid request body",
        received: typeof req.body,
      });
    }

    console.log(
      "Received webhook update at /api/webhook:",
      JSON.stringify(req.body).substring(0, 200) + "..."
    );

    // Process the update
    await bot.handleUpdate(req.body);

    // Return success
    return res.status(200).json({ success: true });
  } catch (error) {
    console.error("Error handling webhook:", error);
    return res.status(500).json({
      error: "Failed to process update",
      message: error.message,
    });
  }
}
