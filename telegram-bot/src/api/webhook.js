import bot from "../index.js";

export default async function handler(req, res) {
  // Only accept POST requests
  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
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
