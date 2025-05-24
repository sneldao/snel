export class ApiService {
  private apiUrl: string;
  private baseUrl: string;

  constructor() {
    // Set the base URL based on environment
    this.baseUrl =
      process.env.NODE_ENV === "production" ? "" : "http://localhost:8000";

    // API prefix is now /api/v1 to match backend
    this.apiUrl = `${this.baseUrl}/api/v1`;
  }

  private getApiKeys() {
    if (typeof window === "undefined") return {};
    return {
      openaiKey: localStorage.getItem("openai_api_key") || "",
      alchemyKey: localStorage.getItem("alchemy_api_key") || "",
      coingeckoKey: localStorage.getItem("coingecko_api_key") || "",
    };
  }

  private getHeaders() {
    const { openaiKey, alchemyKey, coingeckoKey } = this.getApiKeys();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (openaiKey) headers["X-OpenAI-Key"] = openaiKey;
    if (alchemyKey) headers["X-Alchemy-Key"] = alchemyKey;
    if (coingeckoKey) headers["X-CoinGecko-Key"] = coingeckoKey;

    return headers;
  }

  async processCommand(
    command: string,
    walletAddress?: string,
    chainId?: number,
    userName?: string
  ) {
    // Check if this is a swap command - support multiple formats
    const swapMatch = command.match(
      /swap\s+(?:\$?[\d\.]+\s+(?:of|worth\s+of)\s+\S+\s+(?:to|for)\s+\S+|[\d\.]+\s+\S+\s+(?:to|for)\s+\S+)/i
    );
    if (swapMatch) {
      return this.processSwapCommand(command, walletAddress, chainId);
    }

    // Check if this is a bridge command
    const bridgeMatch = command.match(
      /bridge\s+[\d\.]+\s+\S+\s+(?:from\s+\S+\s+)?to\s+\S+/i
    );
    if (bridgeMatch) {
      // For now, let it go through the chat endpoint which will recognize it
      // In the future, we could add a dedicated processBridgeCommand method
    }

    // For other commands, use the chat endpoint
    const response = await fetch(`${this.apiUrl}/chat/process-command`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        command,
        wallet_address: walletAddress,
        chain_id: chainId || 1,
        user_name: userName,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `Error ${response.status}: ${response.statusText}`
      );
    }

    return response.json();
  }

  async processSwapCommand(
    command: string,
    walletAddress?: string,
    chainId?: number
  ) {
    if (!walletAddress) {
      return {
        content: "Please connect your wallet to perform swaps.",
        agent_type: "default",
        status: "error",
      };
    }

    if (!chainId) {
      return {
        content: "Please connect to a supported network to perform swaps.",
        agent_type: "default",
        status: "error",
      };
    }

    const response = await fetch(`${this.apiUrl}/swap/process-command`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        command,
        wallet_address: walletAddress,
        chain_id: chainId,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `Error ${response.status}: ${response.statusText}`
      );
    }

    return response.json();
  }

  async getSwapQuotes(walletAddress?: string, chainId?: number) {
    const response = await fetch(`${this.apiUrl}/swap/get-quotes`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        wallet_address: walletAddress,
        chain_id: chainId || 1,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `Error ${response.status}: ${response.statusText}`
      );
    }

    return response.json();
  }

  async executeSwap(
    walletAddress?: string,
    chainId?: number,
    selectedQuote?: any
  ) {
    const response = await fetch(`${this.apiUrl}/swap/execute`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        wallet_address: walletAddress,
        chain_id: chainId || 1,
        selected_quote: selectedQuote,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `Error ${response.status}: ${response.statusText}`
      );
    }

    return response.json();
  }

  async processDCACommand(
    command: string,
    walletAddress?: string,
    chainId?: number
  ) {
    const response = await fetch(`${this.apiUrl}/dca/process-command`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        content: command,
        wallet_address: walletAddress,
        chain_id: chainId || 1,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `Error ${response.status}: ${response.statusText}`
      );
    }

    return response.json();
  }

  // Multi-step transaction methods
  async completeTransactionStep(
    walletAddress: string,
    chainId: number,
    txHash: string,
    success: boolean = true,
    error?: string
  ) {
    const response = await fetch(`${this.apiUrl}/swap/complete-step`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        wallet_address: walletAddress,
        chain_id: chainId,
        tx_hash: txHash,
        success,
        error,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to complete transaction step: ${response.statusText}`);
    }

    return response.json();
  }

  async getTransactionFlowStatus(walletAddress: string) {
    const response = await fetch(`${this.apiUrl}/swap/flow-status/${walletAddress}`, {
      method: "GET",
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Failed to get flow status: ${response.statusText}`);
    }

    return response.json();
  }

  async cancelTransactionFlow(walletAddress: string, chainId: number) {
    const response = await fetch(`${this.apiUrl}/swap/cancel-flow`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        wallet_address: walletAddress,
        chain_id: chainId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to cancel flow: ${response.statusText}`);
    }

    return response.json();
  }
}
