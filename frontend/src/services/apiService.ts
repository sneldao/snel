import {
  PortfolioService,
  PortfolioAnalysis,
  AnalysisProgress,
} from "./portfolioService";
import { websocketService } from "./websocketService";
// Removed: Using unified backend parsing instead of intentRouter
import { axelarService } from "./axelarService";
import { PortfolioGatekeeper, PortfolioSettings } from "./portfolioGatekeeper";
import { logger } from "../utils/logger";

export class ApiService {
  private apiUrl: string;
  private baseUrl: string;
  private _portfolioService: PortfolioService | null = null;

  constructor() {
    // Set the base URL based on environment
    this.baseUrl =
      process.env.NODE_ENV === "production"
        ? "https://p02--snel-web-app--wxd25gkpcp8m.code.run"
        : "http://localhost:8000";

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
    onProgress?: (progress: AnalysisProgress) => void,
    signer?: unknown, // ethers.Signer for Axelar transactions
    portfolioSettings?: PortfolioSettings
  ) {
    // Portfolio gatekeeper check
    const gatekeeperResult = PortfolioGatekeeper.shouldRunPortfolioAnalysis(
      command, 
      portfolioSettings
    );

    if (!gatekeeperResult.shouldRun && gatekeeperResult.action === 'show_enable_prompt') {
      return PortfolioGatekeeper.createDisabledResponse();
    }

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

      // Check cache first
      if (portfolioSettings?.cacheEnabled) {
        const cached = PortfolioGatekeeper.getCachedData(walletAddress);
        if (cached) {
          return PortfolioGatekeeper.createCachedResponse(cached);
        }
      }
      
      try {
        // Use WebSocket for real-time updates
        const analysis = await this.portfolioService.analyzePortfolio(
          command,
          walletAddress,
          chainId,
          onProgress
        );

        // Cache the result
        if (portfolioSettings?.cacheEnabled) {
          PortfolioGatekeeper.setCachedData(walletAddress, analysis);
        }

        return {
          content: {
            analysis,
            type: "portfolio",
          },
          agentType: "agno",
          status: "success",
        };
      } catch (error) {
        logger.error("Portfolio analysis failed:", error);
        
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

    // All cross-chain operations are now handled by the unified backend

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
    selectedQuote?: Record<string, unknown>
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
  async executePortfolioAction(action: Record<string, unknown>) {
    try {
      return await this.portfolioService.executeAction(action as any);
    } catch (error) {
      logger.error("Failed to execute portfolio action:", error);
      throw error;
    }
  }

  // Add these methods to support the PortfolioService
  async post(endpoint: string, data: Record<string, unknown>) {
    logger.api("POST", `${this.apiUrl}${endpoint}`, data);

    try {
      const response = await fetch(`${this.apiUrl}${endpoint}`, {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorText = await response.text();
        logger.error("API Error Response:", errorText);
        
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
      logger.debug("Response status:", response.status);
      logger.debug("Response data:", responseData);

      return responseData;
    } catch (error) {
      logger.error("API request failed:", {
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
      logger.error(`Service ${service} availability check failed:`, error);
      return false;
    }
  }

  /**
   * Check if Axelar should be used for the given intent
   * DEPRECATED: Now handled by unified backend
   */
  private shouldUseAxelar(intent: Record<string, unknown>): boolean {
    // Only use Axelar for cross-chain operations with supported chains
    if (!intent.isCrossChain || !intent.fromChain || !intent.toChain) {
      return false;
    }

    // Check if both chains are supported by Axelar
    const fromSupported = axelarService.isChainSupported(intent.fromChain as string);
    const toSupported = axelarService.isChainSupported(intent.toChain as string);
    
    return fromSupported && toSupported;
  }

  /**
   * Check Axelar service availability
   */
  async checkAxelarAvailability(): Promise<boolean> {
    try {
      if (!axelarService.isReady()) {
        return false;
      }

      // Test the service with a real availability check
      const supportedChains = axelarService.getSupportedChains();
      if (supportedChains.length < 2) {
        return false;
      }

      // Check if at least two major chains are active
      const majorChains = ['Ethereum', 'Polygon', 'Avalanche', 'Arbitrum'];
      const availableChains = supportedChains.filter(chain => majorChains.includes(chain));
      
      if (availableChains.length < 2) {
        return false;
      }

      // Test chain activity
      try {
        const [fromChain, toChain] = availableChains.slice(0, 2);
        return await axelarService.areChainsActive([fromChain, toChain]);
      } catch (activityError) {
        logger.warn('Axelar chain activity check failed:', activityError);
        // If activity check fails, assume service is available if we have supported chains
        return true;
      }
    } catch (error) {
      logger.error('Error checking Axelar availability:', error);
      return false;
    }
  }
}
