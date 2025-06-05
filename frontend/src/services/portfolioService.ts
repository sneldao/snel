import { ApiService } from "./apiService";
import { websocketService } from "./websocketService";

// ===== CONSOLIDATED PORTFOLIO TYPES =====
// Single source of truth for all portfolio-related types

export interface PortfolioMetric {
  label: string;
  value: string | number;
  change?: number;
  type: "percentage" | "currency" | "number";
}

export interface PortfolioAction {
  id: string;
  description: string;
  type: "optimize" | "rebalance" | "exit" | "enter" | "retry" | "connect" | "stablecoin_suggestion";
  impact: {
    risk?: number;
    yield?: number;
    gas?: number;
  };
}

export interface PortfolioComposition {
  totalValue: number;
  assetAllocation: {
    tokens: number;
    lps: number;
    nfts: number;
  };
  chainDistribution: Record<string, number>;
}

export interface ExaData {
  protocols_found: number;
  yield_opportunities: number;
  best_apy_found: string;
  search_success: boolean;
  protocols: any[];
}

export interface FirecrawlData {
  // Placeholder for firecrawl data structure
  // This can be expanded when firecrawl integration is implemented
  [key: string]: any;
}



export interface PortfolioData {
  api_calls_made: number;
  portfolio_value: number;
  active_chains: number;
  token_count: number;
  risk_level: string;
}

export interface TokenBalance {
  contractAddress: string;
  tokenBalance: string;
}

export interface TokenMetadata {
  symbol: string;
  name: string;
  decimals: number;
}

export interface ChainTokenData {
  tokens: TokenBalance[];
  metadata: Record<string, TokenMetadata>;
}

export interface RawPortfolioData {
  wallet_address: string;
  total_portfolio_value_usd: number;
  native_value_usd: number;
  token_value_usd: number;
  native_balances: Record<string, any>;
  token_balances: Record<string, ChainTokenData>;
  chain_distribution: Record<string, any>;
  risk_score: number;
  diversification_score: number;
  total_tokens: number;
  chains_active: number;
  api_calls_made: number;
  analysis_timestamp: string;
}

export interface PortfolioAnalysis {
  summary: string;
  fullAnalysis?: string;
  metrics: PortfolioMetric[];
  actions: PortfolioAction[];
  riskScore: number;
  timestamp: string;
  risks: string[];
  composition?: PortfolioComposition;
  keyInsights?: string[];
  opportunities?: string[];
  exa_data?: ExaData;
  firecrawl_data?: FirecrawlData;
  portfolio_data?: PortfolioData;
  raw_data?: RawPortfolioData;
  services_status?: {
    portfolio: boolean;
    exa: boolean;
    firecrawl: boolean;
  };
  tool_calls_summary?: {
    total_calls: number;
    exa_calls: number;
    firecrawl_calls: number;
    portfolio_calls: number;
  };
}

export interface AnalysisProgress {
  stage: string;
  completion: number;
  details?: string;
  type: "progress" | "thought" | "action" | "error";
}

// ===== CLEAN PORTFOLIO SERVICE =====
// Focused only on Agno-powered portfolio analysis

export class PortfolioService {
  private apiService: ApiService;

  constructor(apiService: ApiService) {
    this.apiService = apiService;
  }

  /**
   * Analyze portfolio using WebSocket for real-time updates with real blockchain data
   */
  async analyzePortfolio(
    command: string,
    walletAddress?: string,
    chainId?: number,
    onProgress?: (progress: AnalysisProgress) => void
  ): Promise<PortfolioAnalysis> {
    try {
      // Validate input
      if (!walletAddress) {
        throw new Error("Wallet address is required for portfolio analysis");
      }
      
      // Notify initial progress
      if (onProgress) {
        onProgress({
          stage: "Initializing portfolio analysis...",
          completion: 5,
          type: "progress",
          details: "Connecting to analysis service"
        });
      }

      // Store for analysis result
      let analysisResult: PortfolioAnalysis | null = null;
      let useWebSocket = true;
      
      try {
        // Try WebSocket first
        await websocketService.connect(walletAddress, chainId, {
          onOpen: () => {
            if (onProgress) {
              onProgress({
                stage: "Connected to analysis service",
                completion: 10,
                type: "progress",
                details: "Starting portfolio analysis"
              });
            }
          },
        
          onProgress: (progress) => {
            if (onProgress) {
              onProgress(progress);
            }
          
            // Check for service status updates in progress messages
            if (progress.details && progress.details.includes("unavailable")) {
              console.log("Service unavailability detected:", progress.details);
            }
          },
        
          onResult: (result) => {
            analysisResult = result;
          },
        
          onError: (error) => {
            // Mark WebSocket as failed but don't throw
            useWebSocket = false;
            console.warn("WebSocket error, will fallback to HTTP:", error);
          
            if (onProgress) {
              onProgress({
                stage: `WebSocket unavailable: ${error.message || 'Unknown error'}`,
                completion: 10,
                type: "progress",
                details: "Falling back to traditional API request"
              });
            }
          },
        
          onClose: () => {
            console.log("WebSocket connection closed");
          }
        });
        
        // If WebSocket connected successfully, wait for result
        if (useWebSocket) {
          // Wait for result (timeout after 60 seconds)
          const startTime = Date.now();
          const timeout = 60000; // 60 seconds
          
          while (!analysisResult && Date.now() - startTime < timeout) {
            await new Promise(resolve => setTimeout(resolve, 100));
          }
          
          // Disconnect WebSocket
          websocketService.disconnect();
          
          if (!analysisResult) {
            // Timeout occurred, fallback to HTTP
            useWebSocket = false;
            if (onProgress) {
              onProgress({
                stage: "WebSocket timeout, falling back to HTTP request",
                completion: 10,
                type: "progress",
                details: "The real-time analysis timed out"
              });
            }
          }
        }
      } catch (wsError) {
        // Any error with WebSocket, fallback to HTTP
        useWebSocket = false;
        console.warn("WebSocket connection failed:", wsError);
        if (onProgress) {
          onProgress({
            stage: "Connection to real-time service failed",
            completion: 10,
            type: "progress",
            details: "Falling back to traditional API request"
          });
        }
      }
      
      // Fallback to HTTP request if WebSocket failed or timed out
      if (!useWebSocket || !analysisResult) {
        if (onProgress) {
          onProgress({
            stage: "Sending portfolio analysis request",
            completion: 20,
            type: "progress",
            details: "Using traditional API request"
          });
        }
        
        // Create payload for HTTP request with real-time preference
        const payload = {
          prompt: command.trim(),
          wallet_address: walletAddress,
          chain_id: chainId,
          // Signal to backend to skip unavailable services rather than failing
          skip_unavailable_services: true,
          // Set a reasonable timeout to prevent hanging
          timeout: 30000
        };
        
        // Send HTTP request
        if (onProgress) {
          onProgress({
            stage: "Processing portfolio data...",
            completion: 30,
            type: "progress",
            details: "This may take a moment"
          });
        }
        
        try {
          // Use HTTP API instead
          const response = await this.apiService.post(
            "/agno/portfolio-analysis", 
            payload
          );
          
          // Use the HTTP response
          analysisResult = response;
          
          if (onProgress) {
            onProgress({
              stage: "Portfolio data received",
              completion: 90,
              type: "progress",
              details: "Processing results"
            });
          }
        } catch (httpError) {
          // Handle HTTP errors gracefully
          console.error("HTTP portfolio analysis failed:", httpError);
          
          // Create a minimal response structure with error information
          analysisResult = {
            summary: "Unable to complete portfolio analysis",
            fullAnalysis: `Analysis failed: ${httpError instanceof Error ? httpError.message : "Unknown error"}`,
            metrics: [],
            actions: [
              {
                id: "retry_analysis",
                description: "Retry analysis with available services",
                type: "retry",
                impact: {}
              }
            ],
            riskScore: 0,
            timestamp: new Date().toISOString(),
            risks: ["Analysis failed due to service unavailability"],
            keyInsights: ["Some services are currently unavailable. Please try again later."],
            opportunities: [],
            services_status: {
              portfolio: false,
              exa: false,
              firecrawl: false
            }
          };
          
          if (onProgress) {
            onProgress({
              stage: "Analysis failed",
              completion: 100,
              type: "error",
              details: httpError instanceof Error ? httpError.message : "Unknown error"
            });
          }
        }
      }
      
      // Format the response (we should have a result by now, either from WebSocket or HTTP)
      if (!analysisResult) {
        throw new Error("Failed to retrieve portfolio analysis");
      }
      
      const analysis = this.formatAnalysisResponse(analysisResult);
      
      // Send completion notification
      if (onProgress) {
        onProgress({
          stage: "Analysis complete!",
          completion: 100,
          type: "progress",
          details: "Portfolio analysis finished successfully"
        });
      }
      
      return analysis;
    } catch (error) {
      console.error("Portfolio analysis failed:", error);
      
      // Ensure WebSocket is disconnected
      websocketService.disconnect();

      if (onProgress) {
        onProgress({
          stage: "Analysis failed",
          completion: 0,
          type: "error",
          details: error instanceof Error ? error.message : "Unknown error",
        });
      }

      throw error;
    }
  }

  /**
   * Format the raw API response into structured PortfolioAnalysis
   */
  private formatAnalysisResponse(response: any): PortfolioAnalysis {
    console.log("Raw portfolio analysis response:", response);

    // Handle the response structure from the backend
    const analysis = response.analysis || response;

    // Extract content - handle both string and object responses
    let summary = "";
    let fullAnalysis = "";

    if (typeof analysis.summary === "string") {
      summary = analysis.summary;
    } else if (analysis.summary && typeof analysis.summary === "object") {
      // Handle RunResponse object
      summary = analysis.summary.content || String(analysis.summary);
    }

    if (typeof analysis.fullAnalysis === "string") {
      fullAnalysis = analysis.fullAnalysis;
    } else if (analysis.fullAnalysis && typeof analysis.fullAnalysis === "object") {
      fullAnalysis = analysis.fullAnalysis.content || String(analysis.fullAnalysis);
    } else {
      fullAnalysis = summary; // Fallback to summary
    }

    // Initialize services status if not provided
    const services_status = response.services_status || {
      portfolio: false,
      exa: false,
      firecrawl: false
    };
    
    // Check if any data is present to infer service status
    if (!services_status.portfolio && response.portfolio_data) {
      services_status.portfolio = true;
    }
    
    if (!services_status.exa && response.exa_data) {
      services_status.exa = true;
    }

    // Create unavailable services message if needed
    let unavailableServices: string[] = [];
    Object.entries(services_status).forEach(([service, status]) => {
      if (!status) unavailableServices.push(service);
    });

    // Create appropriate actions based on service availability
    let actions = analysis.actions || [];
    
    // Add retry action if services are unavailable
    if (unavailableServices.length > 0 && !actions.some((a: PortfolioAction) => a.type === "retry")) {
      actions.push({
        id: "retry_analysis",
        description: "Retry analysis with all services",
        type: "retry",
        impact: {}
      });
    }

    // Append service availability to summary if services are unavailable
    if (unavailableServices.length > 0) {
      const serviceMessage = `\n\nNote: The following services were unavailable: ${unavailableServices.join(', ')}. Some data may be incomplete.`;
      
      if (!summary.includes("services were unavailable")) {
        summary += serviceMessage;
      }
      
      if (fullAnalysis && !fullAnalysis.includes("services were unavailable")) {
        fullAnalysis += serviceMessage;
      }
      
      // Add insights about unavailable services
        const insights = analysis.keyInsights || [];
        if (!insights.some((i: string) => i.includes && i.includes("unavailable"))) {
          insights.push(`Some services are currently unavailable (${unavailableServices.join(', ')}). The analysis is based on available data only.`);
        }
      
        // Add risks related to unavailable services
        const risks = analysis.risks || [];
        if (unavailableServices.includes("portfolio") && !risks.some((r: string) => r.includes && r.includes("portfolio data"))) {
          risks.push("Limited or no portfolio data available, affecting analysis accuracy");
        }
    }

    return {
      summary: summary || "Portfolio analysis completed",
      fullAnalysis: fullAnalysis,
      metrics: analysis.metrics || [],
      actions: actions,
      riskScore: analysis.riskScore || 0,
      timestamp: analysis.timestamp || new Date().toISOString(),
      risks: analysis.risks || [],
      composition: analysis.composition,
      keyInsights: analysis.keyInsights || [],
      opportunities: analysis.opportunities || [],
      exa_data: analysis.exa_data,
      firecrawl_data: analysis.firecrawl_data,
      portfolio_data: analysis.portfolio_data,
      raw_data: response.portfolio_data?.raw_data,
      services_status: services_status,
      tool_calls_summary: analysis.tool_calls_summary,
    };
  }

  /**
   * Execute a portfolio action
   */
  async executeAction(action: PortfolioAction): Promise<any> {
    // Handle different action types
    switch (action.type) {
      case "retry":
        // Return success for retry actions and log analytics
        console.log("User requested retry of portfolio analysis");
        return { 
          success: true, 
          message: "Analysis will be retried",
          actionType: action.type
        };
        
      case "connect":
        // Return success for connect actions
        console.log("User requested wallet connection");
        return {
          success: true,
          message: "Please connect your wallet",
          actionType: action.type
        };

      case "stablecoin_suggestion":
        // Return success for stablecoin suggestion actions
        console.log("User requested stablecoin diversification suggestion");
        return {
          success: true,
          message: "Stablecoin diversification suggestion provided",
          actionType: action.type
        };

      case "rebalance":
        // For rebalance actions, provide a clear message about real implementation
        return { 
          success: false, 
          message: "Rebalancing requires integration with actual DeFi protocols. This feature is coming soon.",
          actionType: "rebalance",
          requires: "protocol_integration",
          service_status: {
            available: false,
            reason: "implementation_pending",
            eta: "Coming soon"
          }
        };
        
      case "optimize":
      case "enter":
      case "exit":
        // For other protocol actions
        return { 
          success: false, 
          message: `The ${action.type} action requires integration with DeFi protocols. This feature is under development.`,
          actionType: action.type,
          requires: "protocol_integration",
          service_status: {
            available: false,
            reason: "implementation_pending",
            eta: "Under development"
          }
        };
        
      default:
        // For actual DeFi protocol interactions, we'd need to implement protocol-specific logic
        console.log("Requested action execution:", action);
        return {
          success: false,
          message: `Action type '${action.type}' is not yet implemented. This requires integration with actual DeFi protocols.`,
          actionType: action.type || "unknown",
          service_status: {
            available: false,
            reason: "not_implemented",
            eta: "Not scheduled"
          }
        };
    }
  }
}
