// In production, NEXT_PUBLIC_API_URL will be undefined, so we'll use relative paths
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function processCommand(command: string, openaiKey: string) {
  try {
    const response = await fetch(`${API_BASE}/api/process-command`, {
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
