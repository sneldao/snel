/**
 * Unified Command Service - Single Source of Truth for Command Processing
 * 
 * PRINCIPLE: DRY - All command parsing logic consolidated here
 * PRINCIPLE: CLEAN - Clear separation between frontend UX and parsing logic
 * PRINCIPLE: MODULAR - Composable service that can be used across components
 */

import { ApiService } from './apiService';
import { Response } from '../types/responses';

export interface CommandPreview {
  type: string;
  tokens: string[];
  amount?: string;
  isUsdAmount?: boolean;
  isValid: boolean;
  suggestions?: string[];
}

export class CommandService {
  private static instance: CommandService;
  private apiService: ApiService;

  private constructor() {
    this.apiService = new ApiService();
  }

  public static getInstance(): CommandService {
    if (!CommandService.instance) {
      CommandService.instance = new CommandService();
    }
    return CommandService.instance;
  }

  /**
   * Get command preview for UI feedback (lightweight, no backend call)
   * PRINCIPLE: PERFORMANT - Quick local preview without network calls
   */
  public getCommandPreview(command: string): CommandPreview {
    const lowerCommand = command.toLowerCase().trim();
    
    // Quick pattern matching for UI feedback only
    const swapMatch = lowerCommand.match(/swap\s+(?:\$?([\d.]+)\s*(?:of\s+)?(\w+)\s+(?:to|for)\s+(\w+))/);
    const bridgeMatch = lowerCommand.match(/bridge\s+([\d.]+)\s+(\w+)\s+to\s+(\w+)/);
    
    if (swapMatch) {
      const [, amount, fromToken, toToken] = swapMatch;
      return {
        type: 'swap',
        tokens: [fromToken.toUpperCase(), toToken.toUpperCase()],
        amount,
        isUsdAmount: command.includes('$'),
        isValid: true
      };
    }
    
    if (bridgeMatch) {
      const [, amount, token, chain] = bridgeMatch;
      return {
        type: 'bridge',
        tokens: [token.toUpperCase()],
        amount,
        isValid: true
      };
    }
    
    return {
      type: 'unknown',
      tokens: [],
      isValid: false,
      suggestions: [
        'Try: swap 1 usdc to eth',
        'Try: bridge 100 usdc to arbitrum',
        'Try: balance'
      ]
    };
  }

  /**
   * Execute command using backend unified parser
   * PRINCIPLE: SINGLE SOURCE OF TRUTH - Backend handles all parsing logic
   */
  public async executeCommand(
    command: string, 
    walletAddress?: string, 
    chainId?: number
  ): Promise<Response> {
    return this.apiService.processCommand(command, walletAddress, chainId);
  }

  /**
   * Get command suggestions based on context
   * PRINCIPLE: MODULAR - Reusable suggestion logic
   */
  public getSmartSuggestions(
    partialCommand: string,
    tokenBalances?: any[],
    chainId?: number
  ): string[] {
    const suggestions: string[] = [];
    const lower = partialCommand.toLowerCase();

    // Context-aware suggestions
    if (lower.includes('swap') && tokenBalances?.length) {
      const topToken = tokenBalances[0];
      suggestions.push(`swap 0.1 ${topToken.symbol} for USDC`);
      suggestions.push(`swap $100 of ${topToken.symbol} to ETH`);
    }

    if (lower.includes('bridge') && tokenBalances?.length) {
      const topToken = tokenBalances[0];
      suggestions.push(`bridge 100 ${topToken.symbol} to arbitrum`);
    }

    if (!lower.trim()) {
      suggestions.push('swap 1 usdc to eth', 'balance', 'bridge 100 usdc to arbitrum');
    }

    return suggestions;
  }
}

// Export singleton instance
export const commandService = CommandService.getInstance();