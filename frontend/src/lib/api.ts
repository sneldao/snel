// API base URL - use relative path in production
const API_BASE =
  process.env.NODE_ENV === "production"
    ? ""
    : process.env.NEXT_PUBLIC_API_URL || "";

export async function processCommand(command: string, openaiKey: string) {
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
}
