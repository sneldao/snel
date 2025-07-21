export interface PortfolioSettings {
  enabled: boolean;
  backgroundProcessing?: boolean;
  cacheEnabled?: boolean;
}

export interface PortfolioCache {
  data: any;
  timestamp: number;
  address: string;
}

/**
 * Portfolio Gatekeeper - Controls access to portfolio analysis
 * Works with existing portfolio infrastructure
 */
export class PortfolioGatekeeper {
  private static readonly CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
  private static readonly CACHE_KEY_PREFIX = 'snel_portfolio_';

  /**
   * Intercept portfolio commands and decide how to handle them
   */
  static shouldRunPortfolioAnalysis(
    command: string,
    settings?: PortfolioSettings
  ): {
    shouldRun: boolean;
    reason?: string;
    action?: string;
  } {
    const isPortfolioCommand = /portfolio|allocation|holdings|assets|analyze/i.test(
      command.toLowerCase()
    );

    if (!isPortfolioCommand) {
      return { shouldRun: false, reason: 'not_portfolio_command' };
    }

    if (!settings?.enabled) {
      return {
        shouldRun: false,
        reason: 'portfolio_disabled',
        action: 'show_enable_prompt'
      };
    }

    return { shouldRun: true };
  }

  /**
   * Check if we have cached portfolio data
   */
  static getCachedData(address: string): PortfolioCache | null {
    try {
      const key = `${this.CACHE_KEY_PREFIX}${address}`;
      const cached = localStorage.getItem(key);
      
      if (!cached) return null;
      
      const data: PortfolioCache = JSON.parse(cached);
      const isValid = (Date.now() - data.timestamp) < this.CACHE_DURATION;
      
      if (!isValid) {
        localStorage.removeItem(key);
        return null;
      }
      
      return data;
    } catch {
      return null;
    }
  }

  /**
   * Cache portfolio analysis results
   */
  static setCachedData(address: string, analysisResult: any): void {
    try {
      const key = `${this.CACHE_KEY_PREFIX}${address}`;
      const cache: PortfolioCache = {
        data: analysisResult,
        timestamp: Date.now(),
        address,
      };
      
      localStorage.setItem(key, JSON.stringify(cache));
    } catch (error) {
      console.warn('Failed to cache portfolio data:', error);
    }
  }

  /**
   * Clear cached data for an address
   */
  static clearCache(address: string): void {
    try {
      const key = `${this.CACHE_KEY_PREFIX}${address}`;
      localStorage.removeItem(key);
    } catch (error) {
      console.warn('Failed to clear portfolio cache:', error);
    }
  }

  /**
   * Create a disabled portfolio response
   */
  static createDisabledResponse() {
    return {
      content: {
        type: "portfolio_disabled",
        message: "Portfolio analysis is disabled for faster performance.",
        suggestion: {
          title: "Enable Portfolio Analysis?",
          description: "Get detailed insights about your holdings, risk analysis, and optimization recommendations.",
          features: [
            "Holdings breakdown and allocation analysis",
            "Risk assessment and diversification tips", 
            "Optimization recommendations",
            "Performance tracking"
          ],
          warning: "Analysis takes 10-30 seconds using Exa API, CoinGecko, and other data sources.",
          action: "enable_portfolio"
        }
      },
      agentType: "settings" as const,
      status: "info" as const,
      requires_user_action: true
    };
  }

  /**
   * Create a cached response
   */
  static createCachedResponse(cachedData: PortfolioCache) {
    const ageInMinutes = Math.floor((Date.now() - cachedData.timestamp) / (1000 * 60));
    
    return {
      content: {
        analysis: cachedData.data,
        type: "portfolio",
        cached: true,
        cache_info: {
          age_minutes: ageInMinutes,
          fresh_until: new Date(cachedData.timestamp + this.CACHE_DURATION).toLocaleTimeString()
        }
      },
      agentType: "agno" as const,
      status: "success" as const,
    };
  }
}