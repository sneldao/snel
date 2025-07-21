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
  534352: { name: "Scroll", explorer: "https://scrollscan.com/tx/", axelarName: null },
  324: { name: "zkSync Era", explorer: "https://explorer.zksync.io/tx/", axelarName: null },
  34443: { name: "Mode", explorer: "https://explorer.mode.network/tx/", axelarName: null },
  167004: { name: "Taiko", explorer: "https://explorer.test.taiko.xyz/tx/", axelarName: null },

  // Other Networks
  43114: { name: "Avalanche", explorer: "https://snowtrace.io/tx/", axelarName: "Avalanche" },
  5000: { name: "Mantle", explorer: "https://explorer.mantle.xyz/tx/", axelarName: null },
  81457: { name: "Blast", explorer: "https://blastscan.io/tx/", axelarName: null },
} as const;

export type SupportedChainId = keyof typeof SUPPORTED_CHAINS;
export type ChainConfig = typeof CHAIN_CONFIG[SupportedChainId];