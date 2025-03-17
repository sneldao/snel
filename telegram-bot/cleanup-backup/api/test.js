// Test endpoint for checking if our API routes are working
export default function handler(req, res) {
  // Set CORS headers
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    // Handle CORS preflight requests
    res.status(200).end();
    return;
  }

  // Return basic info about the request
  res.status(200).json({
    message: "API route is working!",
    method: req.method,
    url: req.url,
    timestamp: new Date().toISOString(),
    public: true,
  });
}
