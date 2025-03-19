import { NextRequest, NextResponse } from "next/server";

// API route to check wallet bridge connection status
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const connectionId = params.id;

    if (!connectionId) {
      return NextResponse.json(
        { success: false, error: "Missing connection ID" },
        { status: 400 }
      );
    }

    // Get the base API URL from environment or use the current host
    const apiHost =
      process.env.NEXT_PUBLIC_API_URL || process.env.MAIN_DOMAIN || "";
    const apiUrl = `${apiHost}/api/wallet-bridge/status/${connectionId}`;

    // Forward the request to the backend API
    const response = await fetch(apiUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        {
          success: false,
          status: "error",
          error: `Backend API error: ${response.status} ${errorText}`,
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error checking wallet connection status:", error);
    return NextResponse.json(
      {
        success: false,
        status: "error",
        error: error.message || "Internal server error",
      },
      { status: 500 }
    );
  }
}
