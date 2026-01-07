import { NextRequest, NextResponse } from "next/server";

// API route to connect wallet from bridge
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate required fields
    const { connection_id, wallet_address, signature, message } = body;

    if (!connection_id || !wallet_address) {
      return NextResponse.json(
        { success: false, error: "Missing required fields" },
        { status: 400 }
      );
    }

    // Forward to backend API
    const apiHost =
      process.env.NEXT_PUBLIC_API_URL || process.env.MAIN_DOMAIN || "";
    const apiUrl = `${apiHost}/api/wallet-bridge/connect`;

    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        connection_id,
        wallet_address,
        signature: signature || "", // Empty signature if not provided, backend validates
        message: message || "",
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error (${response.status}): ${errorText}`);

      return NextResponse.json(
        {
          success: false,
          error: `API error: ${response.status}`,
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error connecting wallet:", error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || "Internal server error",
      },
      { status: 500 }
    );
  }
}
