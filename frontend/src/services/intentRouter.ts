import { axelarService } from './axelarService';
import { ChainUtils } from '../utils/chainUtils';
// Remove unused import - we handle single-step transactions for cross-chain
// import { multiStepTransactionService } from './multiStepTransactionService';
import { ethers } from 'ethers';

export interface UserIntent {
  type: 'swap' | 'bridge' | 'send' | 'balance';
  fromChain?: string;
  toChain?: string;
  fromToken?: string;
  toToken?: string;
  amount?: string;
  recipient?: string;
  isCrossChain: boolean;
  originalCommand: string;
}

export interface IntentExecutionResult {
  success: boolean;
  txHash?: string;
  error?: string;
  requiresConfirmation?: boolean;
  steps?: Array<{
    description: string;
    status: 'pending' | 'in_progress' | 'completed' | 'failed';
    txHash?: string;
  }>;
}

export class IntentRouter {

  /**
   * Parse natural language command into structured intent
   */
  parseIntent(command: string, currentChainId?: number): UserIntent {
    const lowerCommand = command.toLowerCase();
    
    // Extract tokens
    const tokenRegex = /(\d+(?:\.\d+)?)\s*([a-zA-Z]+)/g;
    const tokens = [...lowerCommand.matchAll(tokenRegex)];
    
    // Extract chain mentions
    const chainMentions = this.extractChainMentions(lowerCommand);
    
    // Determine intent type
    let type: UserIntent['type'] = 'swap';
    if (lowerCommand.includes('bridge') || lowerCommand.includes('move') || lowerCommand.includes('transfer to')) {
      type = 'bridge';
    } else if (lowerCommand.includes('send') || lowerCommand.includes('transfer')) {
      type = 'send';
    } else if (lowerCommand.includes('balance') || lowerCommand.includes('check')) {
      type = 'balance';
    }
    
    // Detect cross-chain intent
    const isCrossChain = this.isCrossChainIntent(lowerCommand, chainMentions, currentChainId);
    
    // Extract amount and tokens
    const amount = tokens[0]?.[1];
    const fromToken = tokens[0]?.[2]?.toUpperCase();
    const toToken = this.extractToToken(lowerCommand);
    
    // Extract chains
    const { fromChain, toChain } = this.extractChains(lowerCommand, chainMentions, isCrossChain, currentChainId);
    
    // Extract recipient for send operations
    const recipient = this.extractRecipient(lowerCommand);

    return {
      type,
      fromChain,
      toChain,
      fromToken,
      toToken,
      amount,
      recipient,
      isCrossChain,
      originalCommand: command
    };
  }

  /**
   * Execute intent with appropriate protocol
   */
  async executeIntent(
    intent: UserIntent, 
    signer: ethers.Signer,
    onProgress?: (message: string, step?: number, total?: number) => void
  ): Promise<IntentExecutionResult> {
    try {
      if (intent.isCrossChain && axelarService.isChainSupported(intent.fromChain || '')) {
        return await this.executeCrossChainIntent(intent, signer, onProgress);
      } else {
        return await this.executeSingleChainIntent(intent, signer, onProgress);
      }
    } catch (error) {
      console.error('Intent execution error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }

  /**
   * Execute cross-chain intent via Axelar
   */
  private async executeCrossChainIntent(
    intent: UserIntent,
    signer: ethers.Signer,
    onProgress?: (message: string, step?: number, total?: number) => void
  ): Promise<IntentExecutionResult> {
    if (!intent.fromChain || !intent.toChain || !intent.fromToken || !intent.amount) {
      return { success: false, error: 'Missing required parameters for cross-chain transfer' };
    }

    onProgress?.('Getting cross-chain quote...', 1, 3);

    try {
      const userAddress = await signer.getAddress();
      const recipientAddress = intent.recipient || userAddress;

      // Get quote first
      const quote = await axelarService.getTransferQuote(
        intent.fromChain,
        intent.toChain,
        intent.fromToken,
        intent.amount
      );

      if (!quote) {
        return { success: false, error: 'Failed to get transfer quote' };
      }

      onProgress?.(`Cross-chain fee: ${quote.fee}. Executing transfer...`, 2, 3);

      // Get provider from signer
      const provider = signer.provider as ethers.BrowserProvider;
      if (!provider) {
        return { success: false, error: 'Web3 provider not available' };
      }

      // Execute the transfer
      const txHash = await axelarService.executeTransfer(
        intent.fromChain,
        intent.toChain,
        recipientAddress,
        intent.fromToken,
        intent.amount,
        provider
      );

      onProgress?.('Transfer initiated! Tracking status...', 3, 3);
      
      return {
        success: true,
        txHash: txHash,
        steps: [
          {
            description: 'Cross-chain transfer initiated',
            status: 'completed',
            txHash: txHash
          },
          {
            description: `Bridging from ${intent.fromChain} to ${intent.toChain}`,
            status: 'in_progress'
          },
          {
            description: `Estimated completion: ${quote.estimatedTime}`,
            status: 'pending'
          }
        ]
      };
    } catch (error) {
      return { 
        success: false, 
        error: `Cross-chain transfer failed: ${error instanceof Error ? error.message : String(error)}` 
      };
    }
  }

  /**
   * Fallback to existing single-chain execution
   */
  private async executeSingleChainIntent(
    intent: UserIntent,
    signer: ethers.Signer,
    onProgress?: (message: string, step?: number, total?: number) => void
  ): Promise<IntentExecutionResult> {
    onProgress?.('Using single-chain execution...', 1, 1);
    
    // This would integrate with your existing swap/transaction services
    // For now, return a placeholder indicating fallback to existing system
    return {
      success: false,
      error: 'Single-chain execution - integrate with existing backend API',
      requiresConfirmation: true
    };
  }

  // Helper methods for parsing
  private extractChainMentions(command: string): string[] {
    const chainNames = ChainUtils.getSupportedChainIds().map(id => ChainUtils.getChainName(id).toLowerCase());
    const chainKeywords = ['ethereum', 'eth', 'polygon', 'matic', 'base', 'arbitrum', 'arb', 'optimism', 'op', 'avalanche', 'avax', 'binance', 'bsc', 'bnb'];
    
    const allChains = [...chainNames, ...chainKeywords];
    const mentioned = allChains.filter(chain => command.includes(chain));
    
    return [...new Set(mentioned)]; // Remove duplicates
  }

  private isCrossChainIntent(command: string, chainMentions: string[], currentChainId?: number): boolean {
    // Explicit cross-chain keywords
    if (command.includes('bridge') || command.includes('cross') || command.includes('from') && command.includes('to')) {
      return true;
    }
    
    // Multiple chains mentioned
    if (chainMentions.length > 1) {
      return true;
    }
    
    // Single chain mentioned but different from current
    if (chainMentions.length === 1 && currentChainId) {
      const mentionedChain = this.normalizeChainName(chainMentions[0]);
      const currentChain = ChainUtils.getChainName(currentChainId);
      return mentionedChain !== currentChain?.toLowerCase();
    }
    
    return false;
  }

  private extractChains(command: string, chainMentions: string[], isCrossChain: boolean, currentChainId?: number): { fromChain?: string, toChain?: string } {
    if (!isCrossChain) {
      const chainName = currentChainId ? ChainUtils.getAxelarChainName(currentChainId) || ChainUtils.getChainName(currentChainId) : undefined;
      return { fromChain: chainName, toChain: chainName };
    }
    
    // Look for "from X to Y" pattern
    const fromToMatch = command.match(/from\s+(\w+)\s+to\s+(\w+)/i);
    if (fromToMatch) {
      return {
        fromChain: this.normalizeChainName(fromToMatch[1]),
        toChain: this.normalizeChainName(fromToMatch[2])
      };
    }
    
    // Look for "on X" pattern (destination chain)
    const onChainMatch = command.match(/on\s+(\w+)/i);
    if (onChainMatch && currentChainId) {
      return {
        fromChain: ChainUtils.getAxelarChainName(currentChainId) || ChainUtils.getChainName(currentChainId),
        toChain: this.normalizeChainName(onChainMatch[1])
      };
    }
    
    // Fallback: use mentioned chains
    if (chainMentions.length >= 2) {
      return {
        fromChain: this.normalizeChainName(chainMentions[0]),
        toChain: this.normalizeChainName(chainMentions[1])
      };
    }
    
    return {};
  }

  private extractToToken(command: string): string | undefined {
    const forMatch = command.match(/for\s+([a-zA-Z]+)/i);
    if (forMatch) {
      return forMatch[1].toUpperCase();
    }
    
    const toMatch = command.match(/to\s+([a-zA-Z]+)(?:\s|$)/i);
    if (toMatch && !this.isChainName(toMatch[1])) {
      return toMatch[1].toUpperCase();
    }
    
    return undefined;
  }

  private extractRecipient(command: string): string | undefined {
    // Look for addresses (0x...) or ENS names (.eth)
    const addressMatch = command.match(/(0x[a-fA-F0-9]{40})/);
    if (addressMatch) {
      return addressMatch[1];
    }
    
    const ensMatch = command.match(/(\w+\.eth)/);
    if (ensMatch) {
      return ensMatch[1];
    }
    
    return undefined;
  }

  private normalizeChainName(chainName: string): string {
    return ChainUtils.normalizeChainName(chainName);
  }

  private isChainName(token: string): boolean {
    const chainNames = ChainUtils.getSupportedChainIds().map(id => ChainUtils.getChainName(id).toLowerCase());
    const chainKeywords = ['ethereum', 'eth', 'polygon', 'matic', 'base', 'arbitrum', 'arb', 'optimism', 'op', 'avalanche', 'avax', 'binance', 'bsc', 'bnb'];
    
    return [...chainNames, ...chainKeywords].includes(token.toLowerCase());
  }
}

// Export singleton instance
export const intentRouter = new IntentRouter();