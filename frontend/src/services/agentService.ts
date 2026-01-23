// AgnoResponse moved to portfolioService.ts to avoid duplication
// Using native browser WebSocket instead of ws package
import { PortfolioAction } from "./portfolioService";

export interface AgentMetadata {
  id: string;
  name: string;
  type: "ChainScope-X" | "TrendSage-X" | "AlphaQuest-X";
  description: string;
  capabilities: string[];
  confidence: number;
  specialization?: {
    chains: string[];
    protocols: string[];
    strategies: string[];
  };
}

export interface AgentProgress {
  stage: string;
  completion: number;
  type: "progress" | "thought" | "action" | "error";
  timestamp: number;
  agent: string;
  metadata?: {
    reasoning?: string[];
    confidence?: number;
    chainContext?: string[];
    gasEstimates?: {
      slow: number;
      medium: number;
      fast: number;
    };
    bridgingOptions?: Array<{
      path: string[];
      estimatedTime: number;
      estimatedCost: number;
      reliability: number;
    }>;
  };
}

export interface CrossChainMetrics {
  bridgingEfficiency: number;
  gasOptimization: number;
  pathReliability: number;
  estimatedSavings: number;
}

// Portfolio types moved to portfolioService.ts to avoid duplication

export interface WorkflowStageData {
  summary: string;
  metrics: Array<{
    label: string;
    value: number | string;
    change?: number;
    confidence?: number;
    trend?: "up" | "down" | "stable";
    prediction?: {
      value: number;
      confidence: number;
      timeframe: string;
    };
  }>;
  insights: string[];
  status: string;
  timestamp: string;
  actions?: any[]; // PortfolioAction moved to portfolioService.ts
  crossChainAnalytics?: {
    opportunities: Array<{
      description: string;
      chains: string[];
      potential_gain: number;
      risk_level: string;
      confidence: number;
    }>;
    bridging_efficiency: {
      current: number;
      potential: number;
      recommendations: string[];
    };
    gas_optimization: {
      current_strategy: string;
      recommended_strategy: string;
      estimated_savings: number;
    };
  };
}

export interface AgentWorkflow {
  id: string;
  name: string;
  stages: {
    id: string;
    name: string;
    agent: AgentMetadata;
    status: "pending" | "active" | "completed" | "error";
    progress: number;
    output?: WorkflowStageData;
    error?: {
      code: string;
      message: string;
      recovery_options?: string[];
      alternative_paths?: string[];
    };
  }[];
  context: {
    chainId?: number;
    timestamp: number;
    userPreferences?: any;
    crossChainContext?: {
      activeChains: string[];
      bridgingPreferences: {
        maxSlippage: number;
        preferredBridges: string[];
      };
      gasPreferences: {
        maxGasPrice: number;
        priorityLevel: "economic" | "balanced" | "fast";
      };
    };
  };
}

export class AgentService {
  private readonly agents: AgentMetadata[] = [
    {
      id: "chainscope",
      name: "ChainScope-X",
      type: "ChainScope-X",
      description: "Advanced portfolio analysis and risk assessment specialist",
      capabilities: [
        "portfolio-analysis",
        "risk-assessment",
        "cross-chain-analytics",
        "gas-optimization",
        "bridging-efficiency",
      ],
      confidence: 0.95,
      specialization: {
        chains: ["Ethereum", "Base", "Optimism", "Arbitrum"],
        protocols: ["Uniswap", "Aave", "Compound", "Balancer"],
        strategies: ["yield-farming", "liquidity-provision", "arbitrage"],
      },
    },
    {
      id: "trendsage",
      name: "TrendSage-X",
      type: "TrendSage-X",
      description:
        "Market trends and opportunity identification expert with predictive capabilities",
      capabilities: [
        "market-analysis",
        "trend-identification",
        "opportunity-detection",
        "predictive-analytics",
        "sentiment-analysis",
      ],
      confidence: 0.92,
      specialization: {
        chains: ["all"],
        protocols: ["all"],
        strategies: ["trend-following", "momentum", "mean-reversion"],
      },
    },
    {
      id: "alphaquest",
      name: "AlphaQuest-X",
      type: "AlphaQuest-X",
      description:
        "Strategy optimization and execution specialist with cross-chain expertise",
      capabilities: [
        "strategy-optimization",
        "execution-planning",
        "risk-mitigation",
        "cross-chain-routing",
        "MEV-protection",
      ],
      confidence: 0.88,
      specialization: {
        chains: ["all"],
        protocols: ["all"],
        strategies: [
          "smart-routing",
          "MEV-aware-execution",
          "flash-loan-arbitrage",
        ],
      },
    },
  ];

  private wsConnection: WebSocket | null = null;
  private progressCallbacks: Set<(progress: AgentProgress) => void> = new Set();

  constructor() {
    this.initializeWebSocket();
  }

  private initializeWebSocket() {
    // Initialize WebSocket connection for real-time updates
    this.wsConnection = new WebSocket(
      process.env.REACT_APP_WS_ENDPOINT || "ws://localhost:8080"
    );

    this.wsConnection.onmessage = (event: MessageEvent) => {
      const progress: AgentProgress = JSON.parse(event.data.toString());
      this.notifyProgressCallbacks(progress);
    };

    this.wsConnection.onerror = (error: ErrorEvent) => {
      console.error("WebSocket error:", error);
      // Implement reconnection logic
      setTimeout(() => this.initializeWebSocket(), 5000);
    };
  }

  private notifyProgressCallbacks(progress: AgentProgress) {
    this.progressCallbacks.forEach((callback) => callback(progress));
  }

  public subscribeToProgress(callback: (progress: AgentProgress) => void) {
    this.progressCallbacks.add(callback);
    return () => this.progressCallbacks.delete(callback);
  }

  public getAgent(type: AgentMetadata["type"]): AgentMetadata {
    const agent = this.agents.find((a) => a.type === type);
    if (!agent) {
      throw new Error(`Agent type ${type} not found`);
    }
    return agent;
  }

  public createWorkflow(): AgentWorkflow {
    return {
      id: crypto.randomUUID(),
      name: "Advanced DeFi Portfolio Analysis",
      stages: this.agents.map((agent) => ({
        id: agent.id,
        name: agent.name,
        agent: agent,
        status: "pending" as const,
        progress: 0,
      })),
      context: {
        timestamp: Date.now(),
        crossChainContext: {
          activeChains: ["Ethereum", "Base", "Optimism", "Arbitrum"],
          bridgingPreferences: {
            maxSlippage: 0.5,
            preferredBridges: ["Hop", "Across", "Connext"],
          },
          gasPreferences: {
            maxGasPrice: 100, // in gwei
            priorityLevel: "balanced",
          },
        },
      },
    };
  }

  public updateWorkflowStage(
    workflow: AgentWorkflow,
    stageId: string,
    update: Partial<AgentWorkflow["stages"][0]>
  ): AgentWorkflow {
    return {
      ...workflow,
      stages: workflow.stages.map((stage) =>
        stage.id === stageId ? { ...stage, ...update } : stage
      ),
    };
  }

  public async optimizeGasStrategy(
    chainId: number,
    action: PortfolioAction
  ): Promise<{
    optimal_time: string;
    estimated_savings: number;
    confidence: number;
  }> {
    // Implementation for gas optimization strategy
    return {
      optimal_time: new Date(Date.now() + 3600000).toISOString(), // Example: 1 hour from now
      estimated_savings: 25.5, // Example: 25.5% savings
      confidence: 0.85,
    };
  }

  public async analyzeCrossChainOpportunities(
    sourceChain: string,
    targetChain: string
  ): Promise<{
    opportunities: Array<{
      type: string;
      potential_gain: number;
      risk_level: string;
      execution_complexity: string;
    }>;
  }> {
    // Implementation for cross-chain opportunity analysis
    return {
      opportunities: [
        {
          type: "arbitrage",
          potential_gain: 2.5,
          risk_level: "medium",
          execution_complexity: "low",
        },
        // Add more opportunities
      ],
    };
  }
}
