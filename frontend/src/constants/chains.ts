/**
 * Canonical chain IDs used throughout the frontend.
 * Exposed as an enum to allow type–safe imports, e.g.:
 *   import { ChainId } from \"@/constants/chains\";
 *   const polygonTokens = getTokensByChain(ChainId.POLYGON);
 *
 * IMPORTANT: The numeric values MUST stay in-sync with SUPPORTED_CHAINS below.
 */
export enum ChainId {
  // Layer 1
  ETHEREUM = 1,
  BSC = 56,
  GNOSIS = 100,

  // Layer 2 & Rollups
  BASE = 8453,
  OPTIMISM = 10,
  ARBITRUM = 42161,
  POLYGON = 137,
  LINEA = 59144,
  SCROLL = 534352,
  ZKSYNC_ERA = 324,
  MODE = 34443,
  TAIKO = 167004,

  // Other Networks
  AVALANCHE = 43114,
  MANTLE = 5000,
  BLAST = 81457,
  KAIA = 8217,
}

export const SUPPORTED_CHAINS = {
  // Layer 1
  1: "Ethereum",
  56: "BSC",
  100: "Gnosis",

  // Layer 2 & Rollups
  8453: "Base",
  10: "Optimism",
  42161: "Arbitrum",
  137: "Polygon",
  59144: "Linea",
  534352: "Scroll",
  324: "zkSync Era",
  34443: "Mode",
  167004: "Taiko",

  // Other Networks
  43114: "Avalanche",
  5000: "Mantle",
  81457: "Blast",
  8217: "Kaia",
} as const;

export const BLOCK_EXPLORERS = {
  // Layer 1
  1: "https://etherscan.io/tx/",
  56: "https://bscscan.com/tx/",
  100: "https://gnosisscan.io/tx/",

  // Layer 2 & Rollups
  8453: "https://basescan.org/tx/",
  10: "https://optimistic.etherscan.io/tx/",
  42161: "https://arbiscan.io/tx/",
  137: "https://polygonscan.com/tx/",
  59144: "https://lineascan.build/tx/",
  534352: "https://scrollscan.com/tx/",
  324: "https://explorer.zksync.io/tx/",
  34443: "https://explorer.mode.network/tx/",
  167004: "https://explorer.test.taiko.xyz/tx/",

  // Other Networks
  43114: "https://snowtrace.io/tx/",
  5000: "https://explorer.mantle.xyz/tx/",
  81457: "https://blastscan.io/tx/",
  8217: "https://kaiascan.io/tx/",
} as const;

// Consolidated chain data for various use cases
export const CHAIN_CONFIG = {
  // Layer 1
  1: { name: "Ethereum", explorer: "https://etherscan.io/tx/", axelarName: "Ethereum" },
  56: { name: "BNB Chain", explorer: "https://bscscan.com/tx/", axelarName: "binance" },
  100: { name: "Gnosis", explorer: "https://gnosisscan.io/tx/", axelarName: null },

  // Layer 2 & Rollups
  8453: { name: "Base", explorer: "https://basescan.org/tx/", axelarName: "base" },
  10: { name: "Optimism", explorer: "https://optimistic.etherscan.io/tx/", axelarName: "optimism" },
  42161: { name: "Arbitrum", explorer: "https://arbiscan.io/tx/", axelarName: "Arbitrum" },
  137: { name: "Polygon", explorer: "https://polygonscan.com/tx/", axelarName: "Polygon" },
  59144: { name: "Linea", explorer: "https://lineascan.build/tx/", axelarName: "linea" },
  534352: { name: "Scroll", explorer: "https://scrollscan.com/tx/", axelarName: "scroll" },
  324: { name: "zkSync Era", explorer: "https://explorer.zksync.io/tx/", axelarName: null },
  34443: { name: "Mode", explorer: "https://explorer.mode.network/tx/", axelarName: null },
  167004: { name: "Taiko", explorer: "https://explorer.test.taiko.xyz/tx/", axelarName: null },

  // Other Networks
  43114: { name: "Avalanche", explorer: "https://snowtrace.io/tx/", axelarName: "Avalanche" },
  5000: { name: "Mantle", explorer: "https://explorer.mantle.xyz/tx/", axelarName: null },
  81457: { name: "Blast", explorer: "https://blastscan.io/tx/", axelarName: null },
  8217: { name: "Kaia", explorer: "https://kaiascan.io/tx/", axelarName: null },
} as const;

export type SupportedChainId = keyof typeof SUPPORTED_CHAINS;
export type ChainConfig = typeof CHAIN_CONFIG[SupportedChainId];

// Axelar Gateway Addresses (consolidated from chainMappings.ts)
export const AXELAR_GATEWAY_ADDRESSES: Record<number, string> = {
  [ChainId.ETHEREUM]: "0x4F4495243837681061C4743b74B3eEdf548D56A5",
  [ChainId.POLYGON]: "0x6f015F16De9fC8791b234eF68D486d2bF203FBA8",
  [ChainId.BSC]: "0x304acf330bbE08d1e512eefaa92F6a57871fD895",
  [ChainId.AVALANCHE]: "0x5029C0EFf6C34351a0CEc334542cDb22c7928f78",
  [ChainId.ARBITRUM]: "0xe432150cce91c13a887f7D836923d5597adD8E31",
  [ChainId.OPTIMISM]: "0xe432150cce91c13a887f7D836923d5597adD8E31",
  [ChainId.BASE]: "0xe432150cce91c13a887f7D836923d5597adD8E31",
} as const;

// Axelar Gas Service Addresses (consolidated from chainMappings.ts)
export const AXELAR_GAS_SERVICE_ADDRESSES: Record<number, string> = {
  [ChainId.ETHEREUM]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [ChainId.POLYGON]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [ChainId.BSC]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [ChainId.AVALANCHE]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [ChainId.ARBITRUM]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [ChainId.OPTIMISM]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
  [ChainId.BASE]: "0x2d5d7d31F671F86C782533cc367F14109a082712",
} as const;

// Chain Colors for UI (consolidated from chainMappings.ts)
export const CHAIN_COLORS: Record<string, string> = {
  'Ethereum': '#627EEA',
  'Polygon': '#8247E5',
  'Arbitrum': '#28A0F0',
  'Optimism': '#FF0420',
  'Base': '#0052FF',
  'Avalanche': '#E84142',
  'BSC': '#F0B90B',
  'Kaia': '#00D2FF', // Kaia brand color
} as const;

// Utility functions (consolidated from chainMappings.ts)
export const getAxelarChainName = (chainId: number): string => {
  const config = CHAIN_CONFIG[chainId as SupportedChainId];
  return config?.axelarName || 'ethereum';
};

export const getAxelarGatewayAddress = (chainId: number): string | null => {
  return AXELAR_GATEWAY_ADDRESSES[chainId] || null;
};

export const getAxelarGasServiceAddress = (chainId: number): string | null => {
  return AXELAR_GAS_SERVICE_ADDRESSES[chainId] || null;
};

export const isAxelarSupported = (chainId: number): boolean => {
  return chainId in AXELAR_GATEWAY_ADDRESSES && chainId in AXELAR_GAS_SERVICE_ADDRESSES;
};

export const getSupportedAxelarChains = (): number[] => {
  return Object.keys(AXELAR_GATEWAY_ADDRESSES).map(Number);
};