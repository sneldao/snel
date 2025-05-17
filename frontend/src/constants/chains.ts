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
