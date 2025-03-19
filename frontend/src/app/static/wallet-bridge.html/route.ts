import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

// This route serves the wallet-bridge.html file from the public directory
export async function GET(request: NextRequest) {
  try {
    // Serve the HTML content from our app/static/wallet-bridge.html file
    const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="0;url=/wallet-bridge">
    <title>Redirecting to Wallet Bridge</title>
</head>
<body>
    <p>Redirecting to the Wallet Bridge page...</p>
    <script>
        // Extract URL parameters and forward them to the new location
        const urlParams = new URLSearchParams(window.location.search);
        window.location.href = "/wallet-bridge?" + urlParams.toString();
    </script>
</body>
</html>
    `;

    return new NextResponse(htmlContent, {
      headers: {
        "Content-Type": "text/html",
      },
    });
  } catch (error) {
    console.error("Error serving wallet-bridge.html:", error);
    return NextResponse.json(
      { error: "Failed to serve wallet bridge HTML" },
      { status: 500 }
    );
  }
}
