import { ApiService } from "./apiService";

export interface PortfolioComposition {
  totalValue: number;
  assetAllocation: {
    tokens: number;
    lps: number;
    nfts: number;
  };
  chainDistribution: Record<string, number>;
}

export interface PortfolioAnalysis {
  composition: PortfolioComposition;
  keyInsights: string[];
  risks: string[];
  opportunities: string[];
  recommendations: string[];
}

export interface AgnoResponse {
  content: string;
  agentType: string;
  status: string;
  intermediateSteps: string[];
  summary?: string;
  fullAnalysis?: string;
  analysis?: {
    composition: {
      totalValue: number;
      assetAllocation: {
        tokens: number;
        lps: number;
        nfts: number;
      };
      chainDistribution: Record<string, number>;
    };
    keyInsights: string[];
    risks: string[];
    opportunities: string[];
    recommendations: string[];
  };
  reasoningSteps?: {
    title: string;
    content: string;
  }[];
}

export class AgnoService {
  private apiService: ApiService;
  private baseUrl: string;

  constructor() {
    this.apiService = new ApiService();
    // Set the base URL based on environment
    this.baseUrl =
      process.env.NODE_ENV === "production" ? "" : "http://localhost:8000";
  }

  private parseAnalysis(content: string): PortfolioAnalysis | undefined {
    try {
      // Extract total value
      const totalValueMatch = content.match(/Total Value: \$([0-9,]+)/);
      const totalValue = totalValueMatch
        ? parseFloat(totalValueMatch[1].replace(/,/g, ""))
        : 0;

      // Extract asset allocation
      const tokenMatch = content.match(/Tokens: (\d+)%/);
      const lpsMatch = content.match(/LPs: (\d+)%/);
      const nftsMatch = content.match(/NFTs: (\d+)%/);

      // Extract chain distribution
      const chainDistribution: Record<string, number> = {};
      const chainMatches = content.matchAll(/(\w+): (\d+)%/g);
      for (const match of chainMatches) {
        if (["Tokens", "LPs", "NFTs"].includes(match[1])) continue;
        chainDistribution[match[1]] = parseInt(match[2]);
      }

      // Extract sections
      const keyInsights =
        content
          .match(/(?<=Key Insights\n)([\s\S]*?)(?=\n\s*###|$)/)?.[0]
          .split("\n")
          .filter(
            (line) => line.trim().startsWith("•") || line.trim().startsWith("-")
          )
          .map((line) => line.trim().replace(/^[•-]\s*/, "")) || [];

      const risks =
        content
          .match(/(?<=Risks\n)([\s\S]*?)(?=\n\s*###|$)/)?.[0]
          .split("\n")
          .filter(
            (line) => line.trim().startsWith("•") || line.trim().startsWith("-")
          )
          .map((line) => line.trim().replace(/^[•-]\s*/, "")) || [];

      const opportunities =
        content
          .match(/(?<=Opportunities\n)([\s\S]*?)(?=\n\s*###|$)/)?.[0]
          .split("\n")
          .filter(
            (line) => line.trim().startsWith("•") || line.trim().startsWith("-")
          )
          .map((line) => line.trim().replace(/^[•-]\s*/, "")) || [];

      const recommendations =
        content
          .match(/(?<=Recommendations\n)([\s\S]*?)(?=\n\s*###|$)/)?.[0]
          .split("\n")
          .filter((line) => line.trim().match(/^\d+\.|\•|\-/))
          .map((line) => line.trim().replace(/^(\d+\.|[•-])\s*/, "")) || [];

      return {
        composition: {
          totalValue,
          assetAllocation: {
            tokens: parseInt(tokenMatch?.[1] || "0"),
            lps: parseInt(lpsMatch?.[1] || "0"),
            nfts: parseInt(nftsMatch?.[1] || "0"),
          },
          chainDistribution,
        },
        keyInsights,
        risks,
        opportunities,
        recommendations,
      };
    } catch (error) {
      console.error("Error parsing portfolio analysis:", error);
      return undefined;
    }
  }

  private extractReasoningSteps(
    content: string
  ): { title: string; content: string }[] {
    const steps: { title: string; content: string }[] = [];
    const stepMatches = content.matchAll(
      /Reasoning step \d+[^\n]*\n([\s\S]*?)(?=Reasoning step|\n\s*$)/g
    );

    for (const match of stepMatches) {
      const title = match[0].split("\n")[0].trim();
      const content = match[1].trim();
      steps.push({ title, content });
    }

    return steps;
  }

  async analyzePortfolio(
    prompt: string,
    walletAddress?: string,
    chainId?: number,
    onProgress?: (step: string) => void
  ): Promise<AgnoResponse> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/v1/agno/portfolio-analysis`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            prompt,
            wallet_address: walletAddress,
            chain_id: chainId,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`
        );
      }

      const data = await response.json();

      if (!data || typeof data.result === "undefined") {
        throw new Error("Invalid response format from server");
      }

      // Handle new API format with summary and full_analysis
      const summary = data.summary || data.result;
      const fullAnalysis = data.full_analysis || data.result;
      const formattedContent = summary; // Use summary as the main content

      // Debug logging
      console.log("AgnoService Debug:", {
        hasDataSummary: !!data.summary,
        hasDataFullAnalysis: !!data.full_analysis,
        summaryLength: summary?.length,
        fullAnalysisLength: fullAnalysis?.length,
        dataKeys: Object.keys(data),
        rawData: data, // Add raw data for debugging
      });

      const reasoningSteps = this.extractReasoningSteps(fullAnalysis);
      const analysis = this.parseAnalysis(fullAnalysis);

      // Extract and report intermediate steps
      if (onProgress && reasoningSteps.length > 0) {
        reasoningSteps.forEach((step) => onProgress(step.title));
      }

      return {
        content: formattedContent,
        summary,
        fullAnalysis,
        agentType: "agno",
        status: "success",
        intermediateSteps: reasoningSteps.map((step) => step.title),
        reasoningSteps,
        analysis,
      };
    } catch (error) {
      console.error("Error analyzing portfolio:", error);
      return {
        content:
          error instanceof Error
            ? error.message
            : "Failed to analyze portfolio",
        agentType: "agno",
        status: "error",
        intermediateSteps: [],
        reasoningSteps: [],
      };
    }
  }
}
