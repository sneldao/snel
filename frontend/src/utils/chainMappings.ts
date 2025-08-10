/**
 * Centralized chain mappings and utilities
 * Single source of truth for chain-related constants
 */

export const CHAIN_IDS = {
  ETHEREUM: 1,
  POLYGON: 137,
  BSC: 56,
  AVALANCHE: 43114,
  ARBITRUM: 42161,
  OPTIMISM: 10,
  BASE: 8453,
} as const;

export const AXELAR_CHAIN_NAMES: Record<number, string> = {
  [CHAIN_IDS.ETHEREUM]: 'Ethereum',
  [CHAIN_IDS.POLYGON]: 'Polygon',
  [CHAIN_IDS.BSC]: 'binance',
  [CHAIN_IDS.AVALANCHE]: 'Avalanche',
  [CHAIN_IDS.ARBITRUM]: 'Arbitrum',
  [CHAIN_IDS.OPTIMISM]: 'optimism',
  [CHAIN_IDS.BASE]: 'base',
};

export const AXELAR_GATEWAY_ADDRESSES: Record<number, string> = {
  [CHAIN_IDS.ETHEREUM]: "0x4F4495243837681061C4743b74B3eEdf548D56A5",
  [CHAIN_IDS.POLYGON]: "0x6f015F16De9fC8791b234eF68D486d2bF203FBA8",
  [CHAIN_IDS.BSC]: "0x304acf330bbE08d1e512eefaa92F6a57871fD895",
  [CHAIN_IDS.AVALANCHE]: "0x5029C0EFf6C34351a0CEc334542cDb22c7928f78",
  [CHAIN_IDS.ARBITRUM]: "0xe432150cce91c13a887f7D836923d5597adD8E31",
  [CHAIN_IDS.OPTIMISM]: "0xe432150cce91c13a887f7D836923d5597adD8E31",
  [CHAIN_IDS.BASE]: "0xe432150cce91c13a887f7D836923d5597adD8E31",
};

export const AXELAR_GAS_SERVICE_ADDRESSES: Record<number, string> = {
  [CHAIN_IDS.ETHEREUM]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [CHAIN_IDS.POLYGON]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [CHAIN_IDS.BSC]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [CHAIN_IDS.AVALANCHE]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [CHAIN_IDS.ARBITRUM]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [CHAIN_IDS.OPTIMISM]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [CHAIN_IDS.BASE]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
};

export const CHAIN_COLORS: Record<string, string> = {
  'Ethereum': '#627EEA',
  'Polygon': '#8247E5',
  'Arbitrum': '#28A0F0',
  'Optimism': '#FF0420',
  'Base': '#0052FF',
  'Avalanche': '#E84142',
  'binance': '#F0B90B',
};

/**
 * Get Axelar chain name from chain ID
 */
export const getAxelarChainName = (chainId: number): string => {
  return AXELAR_CHAIN_NAMES[chainId] || 'ethereum';
};

/**
 * Get Axelar Gateway address for chain
 */
export const getAxelarGatewayAddress = (chainId: number): string | null => {
  return AXELAR_GATEWAY_ADDRESSES[chainId] || null;
};

/**
 * Get Axelar Gas Service address for chain
 */
export const getAxelarGasServiceAddress = (chainId: number): string | null => {
  return AXELAR_GAS_SERVICE_ADDRESSES[chainId] || null;
};

/**
 * Check if chain supports Axelar GMP
 */
export const isAxelarSupported = (chainId: number): boolean => {
  return chainId in AXELAR_GATEWAY_ADDRESSES && chainId in AXELAR_GAS_SERVICE_ADDRESSES;
};

/**
 * Get supported Axelar chains
 */
export const getSupportedAxelarChains = (): number[] => {
  return Object.keys(AXELAR_GATEWAY_ADDRESSES).map(Number);
};