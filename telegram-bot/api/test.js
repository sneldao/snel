// Test endpoint for checking if our API routes are working
export default function handler(req, res) {
  // Return basic info about the request
  res.status(200).json({
    message: "API route is working!",
    method: req.method,
    url: req.url,
    headers: req.headers,
    query: req.query,
    body: req.body || null,
    timestamp: new Date().toISOString(),
  });
}
