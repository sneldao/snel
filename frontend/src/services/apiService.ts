import {
  PortfolioService,
  PortfolioAnalysis,
  AnalysisProgress,
} from "./portfolioService";
import { websocketService } from "./websocketService";

export class ApiService {
  private apiUrl: string;
  private baseUrl: string;
  private _portfolioService: PortfolioService | null = null;

  constructor() {
    // Set the base URL based on environment
    this.baseUrl =
      process.env.NODE_ENV === "production" ? "" : "http://localhost:8000";

    // API prefix is now /api/v1 to match backend
    this.apiUrl = `${this.baseUrl}/api/v1`;
  }

  get portfolioService(): PortfolioService {
    if (!this._portfolioService) {
      this._portfolioService = new PortfolioService(this);
    }
    return this._portfolioService;
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
    userName?: string,
    onProgress?: (progress: AnalysisProgress) => void
  ) {
    // Check if this is a portfolio analysis command
    if (
      /portfolio|allocation|holdings|assets|analyze/i.test(
        command.toLowerCase()
      )
    ) {
      if (!walletAddress) {
        return {
          content: {
            error: "Wallet address is required for portfolio analysis",
            type: "error",
          },
          agentType: "agno",
          status: "error",
        };
      }
      
      try {
        // Use WebSocket for real-time updates
        const analysis = await this.portfolioService.analyzePortfolio(
          command,
          walletAddress,
          chainId,
          onProgress
        );

        return {
          content: {
            analysis,
            type: "portfolio",
          },
          agentType: "agno",
          status: "success",
        };
      } catch (error) {
        console.error("Portfolio analysis failed:", error);
        
        // Make sure WebSocket is disconnected
        websocketService.disconnect();
        
        // Return service unavailability information
        return {
          content: {
            error: error instanceof Error ? error.message : "Portfolio analysis failed",
            type: "error",
            serviceStatus: {
              portfolio: false,
              exa: false
            }
          },
          agentType: "agno",
          status: "error",
        };
      }
    }

    // Let swap commands go through the chat endpoint for consistent handling
    // The chat endpoint will detect and route swap commands properly

    // Check if this is a bridge command
    const bridgeMatch = command.match(
      /bridge\s+[\d\.]+\s+\S+\s+(?:from\s+\S+\s+)?to\s+\S+/i
    );
    if (bridgeMatch) {
      // For now, let it go through the chat endpoint which will recognize it
      // In the future, we could add a dedicated processBridgeCommand method
    }

    // For other commands, use the chat endpoint
    const { openaiKey } = this.getApiKeys();
    const response = await fetch(`${this.apiUrl}/chat/process-command`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        command,
        wallet_address: walletAddress,
        chain_id: chainId || 1,
        user_name: userName,
        openai_api_key: openaiKey, // Include OpenAI key in body instead of headers
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
    // Use the unified chat endpoint for consistency
    return this.processCommand(command, walletAddress, chainId);
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
      throw new Error(
        `Failed to complete transaction step: ${response.statusText}`
      );
    }

    return response.json();
  }

  async getTransactionFlowStatus(walletAddress: string) {
    const response = await fetch(
      `${this.apiUrl}/swap/flow-status/${walletAddress}`,
      {
        method: "GET",
        headers: this.getHeaders(),
      }
    );

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

  // Add method to execute portfolio actions
  async executePortfolioAction(action: any) {
    try {
      return await this.portfolioService.executeAction(action);
    } catch (error) {
      console.error("Failed to execute portfolio action:", error);
      throw error;
    }
  }

  // Add these methods to support the PortfolioService
  async post(endpoint: string, data: any) {
    console.log("Sending request to:", `${this.apiUrl}${endpoint}`);
    console.log("Request payload:", JSON.stringify(data, null, 2));

    try {
      const response = await fetch(`${this.apiUrl}${endpoint}`, {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("API Error Response:", errorText);
        
        // Try to parse error as JSON
        try {
          const errorJson = JSON.parse(errorText);
          if (errorJson.detail) {
            throw new Error(errorJson.detail);
          }
        } catch (parseError) {
          // If parsing fails, use the original error
        }
        
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const responseData = await response.json();
      console.log("Response status:", response.status);
      console.log("Response data:", responseData);

      return responseData;
    } catch (error) {
      console.error("API request failed:", {
        endpoint,
        error,
        requestData: data,
      });
      throw error;
    }
  }
  
  /**
   * Check if a service is available by testing the connection
   */
  async checkServiceAvailability(service: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.apiUrl}/health?service=${service}`, {
        method: "GET",
        headers: this.getHeaders(),
      });
      
      return response.ok;
    } catch (error) {
      console.error(`Service ${service} availability check failed:`, error);
      return false;
    }
  }
}
