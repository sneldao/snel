import {
  PortfolioService,
  PortfolioAnalysis,
  AnalysisProgress,
} from "./portfolioService";
import { websocketService } from "./websocketService";
import { intentRouter, UserIntent } from "./intentRouter";
import { axelarService } from "./axelarService";
import { PortfolioGatekeeper, PortfolioSettings } from "./portfolioGatekeeper";

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
    signer?: any, // ethers.Signer for Axelar transactions
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

    // Check for cross-chain intent BEFORE sending to backend
    const intent = intentRouter.parseIntent(command, chainId);
    
    // If cross-chain operation and Axelar supports the chains, handle directly
    if (intent.isCrossChain && signer && this.shouldUseAxelar(intent)) {
      try {
        onProgress?.({
          stage: 'cross_chain_routing',
          completion: 10,
          details: 'Detecting cross-chain operation...',
          type: 'progress'
        });

        const result = await intentRouter.executeIntent(
          intent, 
          signer,
          (message, step, total) => {
            onProgress?.({
              stage: 'cross_chain_execution',
              completion: 30 + ((step || 0) / (total || 3)) * 60,
              details: message,
              type: 'progress'
            });
          }
        );

        if (result.success) {
          return {
            content: {
              type: 'cross_chain_success',
              transaction: { hash: result.txHash },
              steps: result.steps,
              message: `Cross-chain operation initiated successfully!`,
              axelar_powered: true
            },
            agentType: 'bridge',
            status: 'success',
            metadata: {
              intent,
              estimatedTime: result.steps?.[2]?.description || '5-10 minutes'
            }
          };
        } else if (result.requiresConfirmation) {
          // Fall back to backend for complex operations requiring confirmation
          console.log('Cross-chain operation requires backend confirmation, falling back...');
        } else {
          throw new Error(result.error || 'Cross-chain operation failed');
        }
      } catch (error) {
        console.warn('Axelar execution failed, falling back to backend:', error);
        // Continue to backend fallback below
      }
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

  /**
   * Check if Axelar should be used for the given intent
   */
  private shouldUseAxelar(intent: UserIntent): boolean {
    // Only use Axelar for cross-chain operations with supported chains
    if (!intent.isCrossChain || !intent.fromChain || !intent.toChain) {
      return false;
    }

    // Check if both chains are supported by Axelar
    const fromSupported = axelarService.isChainSupported(intent.fromChain);
    const toSupported = axelarService.isChainSupported(intent.toChain);
    
    return fromSupported && toSupported;
  }

  /**
   * Check Axelar service availability
   */
  async checkAxelarAvailability(): Promise<boolean> {
    try {
      // Test with supported chains to see if Axelar is responsive
      const supportedChains = axelarService.getSupportedChains();
      return supportedChains.length > 0;
    } catch (error) {
      console.error('Axelar availability check failed:', error);
      return false;
    }
  }
}
