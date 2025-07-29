import { ParsedCommand, CommandType } from './commandParser';
import { ChainId, SUPPORTED_CHAINS } from '../constants/chains';
import { ethers } from 'ethers';
// Icon used by some consumers of this utility; imported here to avoid runtime missing symbol errors
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { FaHeartbeat } from 'react-icons/fa';

// Gas price data by chain (in gwei)
interface GasPrice {
  slow: number;
  average: number;
  fast: number;
}

interface GasEstimate {
  cost: string;
  time: string;
  gasLimit: number;
  gasPriceGwei: number;
  nativeTokenSymbol: string;
  usdCost?: string;
}

// Default gas prices by chain (in gwei)
const DEFAULT_GAS_PRICES: Record<number, GasPrice> = {
  [ChainId.ETHEREUM]: { slow: 25, average: 40, fast: 60 },
  [ChainId.POLYGON]: { slow: 50, average: 80, fast: 120 },
  [ChainId.ARBITRUM]: { slow: 0.1, average: 0.25, fast: 0.5 },
  [ChainId.OPTIMISM]: { slow: 0.001, average: 0.005, fast: 0.01 },
  [ChainId.BASE]: { slow: 0.001, average: 0.005, fast: 0.01 },
  [ChainId.AVALANCHE]: { slow: 25, average: 35, fast: 50 },
  [ChainId.BSC]: { slow: 3, average: 5, fast: 7 },
};

// Default gas limits by operation type and chain
const DEFAULT_GAS_LIMITS: Record<CommandType, Record<number, number>> = {
  swap: {
    [ChainId.ETHEREUM]: 180000,
    [ChainId.POLYGON]: 250000,
    [ChainId.ARBITRUM]: 800000,
    [ChainId.OPTIMISM]: 250000,
    [ChainId.BASE]: 250000,
    [ChainId.AVALANCHE]: 250000,
    [ChainId.BSC]: 200000,
    default: 200000,
  },
  bridge: {
    [ChainId.ETHEREUM]: 300000,
    [ChainId.POLYGON]: 350000,
    [ChainId.ARBITRUM]: 1000000,
    [ChainId.OPTIMISM]: 350000,
    [ChainId.BASE]: 350000,
    [ChainId.AVALANCHE]: 350000,
    [ChainId.BSC]: 300000,
    default: 300000,
  },
  send: {
    [ChainId.ETHEREUM]: 21000,
    [ChainId.POLYGON]: 21000,
    [ChainId.ARBITRUM]: 100000,
    [ChainId.OPTIMISM]: 21000,
    [ChainId.BASE]: 21000,
    [ChainId.AVALANCHE]: 21000,
    [ChainId.BSC]: 21000,
    default: 21000,
  },
  // Default values for other command types
  analyze: { default: 0 },
  check: { default: 0 },
  info: { default: 0 },
  set: { default: 50000 },
  connect: { default: 0 },
  disconnect: { default: 0 },
  help: { default: 0 },
  stake: { default: 150000 },
  unstake: { default: 150000 },
  provide: { default: 250000 },
  remove: { default: 200000 },
  borrow: { default: 200000 },
  repay: { default: 200000 },
  claim: { default: 120000 },
  alert: { default: 0 },
  schedule: { default: 100000 },
  switch: { default: 0 },
  generate: { default: 0 },
  verify: { default: 0 },
  decode: { default: 0 },
  find: { default: 0 },
  join: { default: 0 },
  share: { default: 0 },
  follow: { default: 0 },
  calculate: { default: 0 },
  show: { default: 0 },
  compare: { default: 0 },
  estimate: { default: 0 },
  unknown: { default: 0 },
};

// Native token prices in USD (for cost estimation)
const NATIVE_TOKEN_PRICES: Record<number, number> = {
  [ChainId.ETHEREUM]: 3500,
  [ChainId.POLYGON]: 0.5,
  [ChainId.ARBITRUM]: 3500, // Uses ETH
  [ChainId.OPTIMISM]: 3500, // Uses ETH
  [ChainId.BASE]: 3500,     // Uses ETH
  [ChainId.AVALANCHE]: 30,
  [ChainId.BSC]: 300,
};

// Native token symbols by chain
const NATIVE_TOKEN_SYMBOLS: Record<number, string> = {
  [ChainId.ETHEREUM]: 'ETH',
  [ChainId.POLYGON]: 'MATIC',
  [ChainId.ARBITRUM]: 'ETH',
  [ChainId.OPTIMISM]: 'ETH',
  [ChainId.BASE]: 'ETH',
  [ChainId.AVALANCHE]: 'AVAX',
  [ChainId.BSC]: 'BNB',
};

// Time estimates by speed (in seconds)
const TIME_ESTIMATES: Record<string, Record<string, number>> = {
  [ChainId.ETHEREUM.toString()]: {
    slow: 300, // 5 minutes
    average: 120, // 2 minutes
    fast: 30, // 30 seconds
  },
  [ChainId.POLYGON.toString()]: {
    slow: 60, // 1 minute
    average: 30, // 30 seconds
    fast: 15, // 15 seconds
  },
  [ChainId.ARBITRUM.toString()]: {
    slow: 30, // 30 seconds
    average: 15, // 15 seconds
    fast: 5, // 5 seconds
  },
  default: {
    slow: 120, // 2 minutes
    average: 60, // 1 minute
    fast: 30, // 30 seconds
  },
};

/**
 * Estimates gas cost for a given command and chain ID
 * 
 * @param command Parsed command object
 * @param chainId ID of the blockchain network
 * @param speedPreference Optional speed preference (slow, average, fast)
 * @returns Estimated gas cost and time information
 */
export async function estimateGasCost(
  command: ParsedCommand, 
  chainId: number,
  speedPreference: 'slow' | 'average' | 'fast' = 'average'
): Promise<{ cost: string; time: string }> {
  try {
    // Get current gas prices (in production, this would fetch from an API)
    const gasPrice = await getGasPrices(chainId);
    
    // Get gas limit based on command type and chain
    const gasLimit = getGasLimit(command, chainId);
    
    // Skip estimation for read-only operations
    if (gasLimit === 0) {
      return { cost: '0', time: 'Instant' };
    }
    
    // Get selected gas price based on speed preference
    const selectedGasPrice = gasPrice[speedPreference];
    
    // Calculate cost in native token
    const gasCostInEth = (selectedGasPrice * gasLimit) / 1e9; // Convert gwei to ETH
    
    // Get native token symbol
    const nativeTokenSymbol = NATIVE_TOKEN_SYMBOLS[chainId] || 'ETH';
    
    // Format cost string
    const formattedCost = formatGasCost(gasCostInEth, nativeTokenSymbol);
    
    // Calculate USD cost if price data is available
    let usdCost = '';
    if (NATIVE_TOKEN_PRICES[chainId]) {
      const costInUsd = gasCostInEth * NATIVE_TOKEN_PRICES[chainId];
      usdCost = `$${costInUsd.toFixed(2)}`;
    }
    
    // Get time estimate
    const timeEstimate = getTimeEstimate(chainId, speedPreference);
    
    // Return formatted result
    const result = {
      cost: usdCost ? `${formattedCost} (${usdCost})` : formattedCost,
      time: timeEstimate,
      gasLimit,
      gasPriceGwei: selectedGasPrice,
      nativeTokenSymbol,
      usdCost
    };
    
    // For bridge operations, add destination gas cost
    if (command.type === 'bridge' && command.targetChain) {
      const destinationEstimate = await estimateDestinationGas(command, command.targetChain);
      if (destinationEstimate) {
        return {
          cost: `${result.cost} + ${destinationEstimate.cost}`,
          time: `${result.time} + ${destinationEstimate.time}`
        };
      }
    }
    
    return {
      cost: result.cost,
      time: result.time
    };
  } catch (error) {
    console.error('Error estimating gas:', error);
    return {
      cost: 'Unknown',
      time: 'Unknown'
    };
  }
}

/**
 * Get current gas prices for a given chain
 * In a production app, this would fetch from a gas price API
 */
async function getGasPrices(chainId: number): Promise<GasPrice> {
  // In production, this would fetch from an API like Etherscan, Blocknative, etc.
  // For now, use default values
  return DEFAULT_GAS_PRICES[chainId] || { slow: 30, average: 50, fast: 80 };
}

/**
 * Get gas limit for a given command and chain
 */
function getGasLimit(command: ParsedCommand, chainId: number): number {
  // Get gas limits for this command type
  const gasLimits = DEFAULT_GAS_LIMITS[command.type];
  
  // Use chain-specific limit if available, otherwise use default
  const gasLimit = gasLimits[chainId] || gasLimits.default || 0;
  
  // Apply modifiers based on command parameters
  let modifiedGasLimit = gasLimit;
  
  // Adjust for token type (ERC20 transfers cost more than native token)
  if (command.type === 'send' && command.sourceToken && command.sourceToken !== 'ETH' && 
      command.sourceToken !== NATIVE_TOKEN_SYMBOLS[chainId]) {
    modifiedGasLimit = 65000; // ERC20 transfer
  }
  
  // Adjust for swap complexity
  if (command.type === 'swap') {
    // Complex swaps (with slippage settings, specific DEX, etc.) cost more
    if (command.slippage !== undefined || command.dex) {
      modifiedGasLimit *= 1.2;
    }
    
    // Token-to-token swaps cost more than ETH-to-token or token-to-ETH
    if (command.sourceToken !== 'ETH' && command.targetToken !== 'ETH' &&
        command.sourceToken !== NATIVE_TOKEN_SYMBOLS[chainId] && 
        command.targetToken !== NATIVE_TOKEN_SYMBOLS[chainId]) {
      modifiedGasLimit *= 1.3;
    }
  }
  
  // Adjust for bridge complexity
  if (command.type === 'bridge') {
    // Bridges with message or custom recipient cost more
    if (command.message || command.recipientAddress) {
      modifiedGasLimit *= 1.2;
    }
  }
  
  return Math.round(modifiedGasLimit);
}

/**
 * Format gas cost with appropriate units
 */
function formatGasCost(cost: number, tokenSymbol: string): string {
  if (cost < 0.0001) {
    return `<0.0001 ${tokenSymbol}`;
  } else if (cost < 0.001) {
    return `${cost.toFixed(5)} ${tokenSymbol}`;
  } else if (cost < 0.01) {
    return `${cost.toFixed(4)} ${tokenSymbol}`;
  } else if (cost < 0.1) {
    return `${cost.toFixed(3)} ${tokenSymbol}`;
  } else {
    return `${cost.toFixed(2)} ${tokenSymbol}`;
  }
}

/**
 * Get time estimate for transaction confirmation
 */
function getTimeEstimate(chainId: number, speedPreference: 'slow' | 'average' | 'fast'): string {
  const chainTimeEstimates = TIME_ESTIMATES[chainId.toString()] || TIME_ESTIMATES.default;
  const seconds = chainTimeEstimates[speedPreference];
  
  if (seconds < 60) {
    return `~${seconds} seconds`;
  } else if (seconds < 3600) {
    return `~${Math.round(seconds / 60)} minutes`;
  } else {
    return `~${Math.round(seconds / 3600)} hours`;
  }
}

/**
 * Estimate gas costs for destination chain in bridge operations
 */
async function estimateDestinationGas(
  command: ParsedCommand,
  destinationChainId: number
): Promise<{ cost: string; time: string } | null> {
  // Skip if destination chain is not supported
  if (!SUPPORTED_CHAINS[destinationChainId]) {
    return null;
  }
  
  // For bridge operations, we need to estimate gas on the destination chain
  // This is typically much lower than source chain gas
  const destinationGasLimit = 100000; // Default destination gas limit
  
  // Get gas price for destination chain
  const gasPrice = await getGasPrices(destinationChainId);
  
  // Use average gas price for destination
  const selectedGasPrice = gasPrice.average;
  
  // Calculate cost in native token
  const gasCostInEth = (selectedGasPrice * destinationGasLimit) / 1e9;
  
  // Get native token symbol for destination chain
  const nativeTokenSymbol = NATIVE_TOKEN_SYMBOLS[destinationChainId] || 'ETH';
  
  // Format cost string
  const formattedCost = formatGasCost(gasCostInEth, nativeTokenSymbol);
  
  // Calculate USD cost if price data is available
  let usdCost = '';
  if (NATIVE_TOKEN_PRICES[destinationChainId]) {
    const costInUsd = gasCostInEth * NATIVE_TOKEN_PRICES[destinationChainId];
    usdCost = `$${costInUsd.toFixed(2)}`;
  }
  
  // Get time estimate for destination chain
  const timeEstimate = getTimeEstimate(destinationChainId, 'average');
  
  return {
    cost: usdCost ? `${formattedCost} (${usdCost})` : formattedCost,
    time: timeEstimate
  };
}

/**
 * Calculate gas cost for a transaction with given parameters
 * Useful for more precise estimates when transaction details are known
 */
export function calculateGasCost(
  gasLimit: number,
  gasPriceGwei: number,
  chainId: number
): { nativeCost: number; usdCost: number | null; nativeToken: string } {
  const gasCostInEth = (gasPriceGwei * gasLimit) / 1e9;
  const nativeToken = NATIVE_TOKEN_SYMBOLS[chainId] || 'ETH';
  
  let usdCost = null;
  if (NATIVE_TOKEN_PRICES[chainId]) {
    usdCost = gasCostInEth * NATIVE_TOKEN_PRICES[chainId];
  }
  
  return {
    nativeCost: gasCostInEth,
    usdCost,
    nativeToken
  };
}

/**
 * Get current base fee for a given chain
 * In a production app, this would fetch from a blockchain node or API
 */
export async function getCurrentBaseFee(chainId: number): Promise<number> {
  // In production, this would fetch the current base fee from a node or API
  // For now, use average gas price as an approximation
  const gasPrice = await getGasPrices(chainId);
  return gasPrice.average;
}

/**
 * Format a detailed gas estimation for UI display
 */
export function formatDetailedGasEstimate(estimate: GasEstimate): {
  costDisplay: string;
  timeDisplay: string;
  detailedInfo: string;
} {
  const costDisplay = estimate.usdCost 
    ? `${estimate.cost}`
    : estimate.cost;
  
  const timeDisplay = estimate.time;
  
  const detailedInfo = `Gas Limit: ${estimate.gasLimit.toLocaleString()} units
Gas Price: ${estimate.gasPriceGwei} Gwei
Estimated Cost: ${estimate.cost}
Estimated Time: ${estimate.time}`;
  
  return {
    costDisplay,
    timeDisplay,
    detailedInfo
  };
}

/**
 * Get gas price tiers for a given chain
 * Useful for displaying gas price options to users
 */
export async function getGasPriceTiers(chainId: number): Promise<{
  slow: { price: number; time: string };
  average: { price: number; time: string };
  fast: { price: number; time: string };
}> {
  const gasPrices = await getGasPrices(chainId);
  
  return {
    slow: {
      price: gasPrices.slow,
      time: getTimeEstimate(chainId, 'slow')
    },
    average: {
      price: gasPrices.average,
      time: getTimeEstimate(chainId, 'average')
    },
    fast: {
      price: gasPrices.fast,
      time: getTimeEstimate(chainId, 'fast')
    }
  };
}
