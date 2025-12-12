/**
 * Command Sequence Analyzer
 * Analyzes sequences of commands to detect opportunities for batching or optimization
 */

import { ParsedCommand } from "./commandParser";

/**
 * Analyzes a sequence of commands to detect batching opportunities
 * @param commands Array of parsed commands
 * @returns Analysis results including batching suggestions
 */
export function analyzeCommandSequence(commands: ParsedCommand[]): {
  transferBatchOpportunity: boolean;
  transferCount: number;
  suggestedBatchSize: number;
  estimatedSavingsPercentage: number;
  chainId?: number;
} {
  // Filter for transfer commands
  const transferCommands = commands.filter(cmd => cmd.type === 'send');
  
  if (transferCommands.length < 2) {
    return {
      transferBatchOpportunity: false,
      transferCount: transferCommands.length,
      suggestedBatchSize: 0,
      estimatedSavingsPercentage: 0
    };
  }
  
  // Check if all transfers are on the same chain
  const chainIds = transferCommands.map(cmd => cmd.sourceChain).filter(Boolean);
  const uniqueChains = [...new Set(chainIds)];
  const chainId = uniqueChains.length === 1 ? uniqueChains[0] : undefined;
  
  // For Scroll and other L2s, batching is particularly beneficial
  const isL2Chain = chainId ? [534352, 42161, 10, 8453, 324].includes(chainId) : false;
  
  // Suggest batching if:
  // 1. Multiple transfers on the same chain
  // 2. On an L2 chain where batching is beneficial
  // 3. At least 2 transfers
  const shouldSuggestBatching = transferCommands.length >= 2 && isL2Chain;
  
  // Estimate savings (simplified model)
  let estimatedSavings = 0;
  if (shouldSuggestBatching) {
    // On L2s, batching can save 20-40% on gas costs
    estimatedSavings = Math.min(20 + (transferCommands.length * 5), 40);
  }
  
  return {
    transferBatchOpportunity: shouldSuggestBatching,
    transferCount: transferCommands.length,
    suggestedBatchSize: shouldSuggestBatching ? transferCommands.length : 0,
    estimatedSavingsPercentage: Math.round(estimatedSavings),
    chainId
  };
}

/**
 * Generates a suggestion message for batching transfers
 * @param analysis Analysis results from analyzeCommandSequence
 * @returns Suggestion message or null if no suggestion
 */
export function generateBatchingSuggestion(analysis: ReturnType<typeof analyzeCommandSequence>): string | null {
  if (!analysis.transferBatchOpportunity) {
    return null;
  }
  
  const chainNames: Record<number, string> = {
    534352: "Scroll",
    42161: "Arbitrum",
    10: "Optimism",
    8453: "Base",
    324: "zkSync Era"
  };
  
  const chainName = analysis.chainId ? chainNames[analysis.chainId] || `Chain ${analysis.chainId}` : "this network";
  
  return `You're making multiple transfers on ${chainName}. Consider batching them to save approximately ${analysis.estimatedSavingsPercentage}% on gas fees.`;
}