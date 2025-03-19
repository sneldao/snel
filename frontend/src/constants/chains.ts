export const SUPPORTED_CHAINS = {
  1: "Ethereum",
  8453: "Base",
  42161: "Arbitrum",
  10: "Optimism",
  137: "Polygon",
  43114: "Avalanche",
  534352: "Scroll",
  324: "zkSync Era",
} as const;

export const BLOCK_EXPLORERS = {
  1: "https://etherscan.io/tx/",
  8453: "https://basescan.org/tx/",
  42161: "https://arbiscan.io/tx/",
  10: "https://optimistic.etherscan.io/tx/",
  137: "https://polygonscan.com/tx/",
  43114: "https://snowtrace.io/tx/",
  534352: "https://scrollscan.com/tx/",
  324: "https://explorer.zksync.io/tx/",
} as const;
