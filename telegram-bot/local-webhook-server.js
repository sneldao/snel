#!/usr/bin/env node
/**
 * Local server to handle Telegram webhook requests
 *
 * This server will receive webhook calls from Telegram and forward them to
 * the main application API for processing. Useful for local development
 * when using ngrok to expose a local server.
 *
 * Usage:
 * node local-webhook-server.js
 */

import dotenv from "dotenv";
import express from "express";
import axios from "axios";
import cors from "cors";

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.WEBHOOK_PORT || 3001;
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const API_URL = process.env.API_URL || "http://localhost:8000/api";

if (!BOT_TOKEN) {
  console.error("Error: TELEGRAM_BOT_TOKEN not found in environment variables");
  process.exit(1);
}

// Middleware
app.use(express.json());
app.use(cors());

// Logging middleware
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next();
});

// Health check endpoint
app.get("/", (req, res) => {
  res.json({
    status: "ok",
    message: "Telegram webhook server is running",
    timestamp: new Date().toISOString(),
  });
});

// Bot info endpoint
app.get("/bot-info", async (req, res) => {
  try {
    const response = await axios.get(
      `https://api.telegram.org/bot${BOT_TOKEN}/getMe`
    );
    res.json(response.data);
  } catch (error) {
    console.error("Error getting bot info:", error.message);
    res.status(500).json({
      status: "error",
      message: "Failed to get bot information",
      error: error.message,
    });
  }
});

// Webhook endpoint
app.post("/webhook", async (req, res) => {
  console.log(
    "Received webhook from Telegram:",
    JSON.stringify(req.body, null, 2)
  );

  try {
    // Forward the webhook payload to the main API
    const apiEndpoint = `${API_URL}/messaging/telegram/webhook`;
    console.log(`Forwarding to API endpoint: ${apiEndpoint}`);

    const apiResponse = await axios.post(apiEndpoint, req.body, {
      headers: {
        "Content-Type": "application/json",
      },
    });

    console.log("API response:", apiResponse.status, apiResponse.data);
    res.status(apiResponse.status).json(apiResponse.data);
  } catch (error) {
    console.error("Error forwarding webhook to API:", error.message);

    if (error.response) {
      console.error(
        "API response:",
        error.response.status,
        error.response.data
      );
    }

    // Always return 200 OK to Telegram to prevent repeated webhook attempts
    res.status(200).json({
      status: "error",
      message: "Error processing webhook",
      error: error.message,
    });
  }
});

// Start the server
app.listen(PORT, () => {
  console.log(`Telegram webhook server running on port ${PORT}`);
  console.log(`Bot webhook endpoint: http://localhost:${PORT}/webhook`);
  console.log(`Health check: http://localhost:${PORT}/`);
  console.log(`Bot info: http://localhost:${PORT}/bot-info`);
  console.log("\nTo set this as your webhook URL:");
  console.log(
    `node webhook-manager.js set https://your-ngrok-url.ngrok-free.app/webhook`
  );
});
