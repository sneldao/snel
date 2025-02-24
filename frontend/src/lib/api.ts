// Force empty API_BASE in production, use env var only in development
const API_BASE =
  process.env.NODE_ENV === "production"
    ? ""
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// In a monorepo, we always use relative paths and let Next.js handle the routing
export async function processCommand(command: string) {
  const response = await fetch(`/api/process-command`, {
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
