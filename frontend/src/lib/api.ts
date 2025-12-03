// Use the environment variable for API base URL
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production"
    ? "https://api.snel.famile.xyz"  // Default production URL
    : "http://localhost:8000");      // Default development URL

// In a monorepo, we always use relative paths and let Next.js handle the routing
export const API_URL = "/api";

export async function processCommand(command: string) {
  const response = await fetch(`${API_BASE}/api/v1/chat/process-command`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ command }),
  });

  if (!response.ok) {
    throw new Error(`Failed to process command: ${response.statusText}`);
  }

  return response.json();
}

export async function executeTransaction(txData: any) {
  const response = await fetch(`/api/execute-transaction`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(txData),
  });

  if (!response.ok) {
    throw new Error(`Failed to execute transaction: ${response.statusText}`);
  }

  return response.json();
}
