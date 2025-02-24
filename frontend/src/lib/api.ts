// Force empty API_BASE in production, use env var only in development
const API_BASE =
  process.env.NODE_ENV === "production"
    ? ""
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// In a monorepo, we always use relative paths and let Next.js handle the routing
export async function processCommand(command: string, openaiKey: string) {
  try {
    // Log the API call (for debugging)
    console.log("Making API call to:", "/api/process-command");

    const response = await fetch("/api/process-command", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-OpenAI-Key": openaiKey,
      },
      body: JSON.stringify({ content: command }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error (${response.status}): ${errorText}`);
    }

    return response.json();
  } catch (error) {
    // Log the actual error for debugging
    console.error("API call failed:", error);
    throw error;
  }
}
