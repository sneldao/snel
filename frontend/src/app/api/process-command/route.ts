import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    // Get the API URL from environment variables
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Parse the request body
    const body = await request.json();

    // Forward the request to the backend API
    const response = await fetch(`${apiUrl}/api/commands/process-command`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    // Check if the response is OK
    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        `Error from API: ${response.status} ${response.statusText}`,
        errorText
      );

      // Return a more helpful error message
      return NextResponse.json(
        {
          error_message: `API Error: ${response.status} ${response.statusText}`,
          detail: errorText,
        },
        { status: response.status }
      );
    }

    // Parse the response
    const data = await response.json();

    // Return the response
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in process-command API route:", error);

    // Return a 500 error
    return NextResponse.json(
      {
        error_message: `Server error: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 500 }
    );
  }
}
